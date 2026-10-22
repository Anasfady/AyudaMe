"""Compara referencias del benchmark; no genera respuestas ni elige ganador."""
import argparse
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
from statistics import mean

from src.common.settings import PROJECT_ROOT, Settings
from src.common.tokenization import load_tokenization
from scripts.index_corpus import record_digest

KS = (3, 4, 5, 8)


def load_questions(path, documents):
    """Respeta el BOM UTF-16 y valida etiquetas sin utilizarlas para buscar."""
    raw = Path(path).read_bytes()
    questions = json.loads(raw)["questions"]
    ids = set()
    if not questions:
        raise ValueError("Benchmark vacío")
    for question in questions:
        key = question["id"]
        if key in ids or not question["question"].strip():
            raise ValueError("ID duplicado o pregunta vacía")
        ids.add(key)
        doc_id = question.get("expected_doc_id")
        page = question.get("expected_page")
        if doc_id is not None and doc_id not in documents:
            raise ValueError(f"{key}: documento esperado desconocido")
        if page is not None and (doc_id is None or type(page) is not int
                                 or not 1 <= page <= documents[doc_id]):
            raise ValueError(f"{key}: página esperada inválida")
    return questions, sha256(raw).hexdigest()


def score_question(question, ranked, k):
    """Aciertos binarios; None significa que falta una referencia para puntuar."""
    if type(k) is not int or k <= 0:
        raise ValueError("k debe ser un entero positivo")
    selected = ranked[:k]
    expected_doc = question.get("expected_doc_id")
    expected_page = question.get("expected_page")
    matching = [r for r in selected if r["metadata"].get("doc_id") == expected_doc]
    return {
        "document_hit": bool(matching) if expected_doc is not None else None,
        "page_hit": any(r["metadata"]["page"] <= expected_page <= r["metadata"]["page_end"]
                        for r in matching) if expected_page is not None else None,
        "retrieved": len(selected),
        # Suma por fragmento: conserva el coste del overlap repetido.
        "text_tokens": sum(r["text_tokens"] for r in selected),
    }


def summarize(rows, k):
    """Denominadores explícitos; los casos sin referencia no cuentan como fallos."""
    scores = [row["scores"][str(k)] for row in rows]
    result = {"k": k, "questions": len(rows)}
    for metric in ("document_hit", "page_hit"):
        values = [s[metric] for s in scores if s[metric] is not None]
        result[metric] = {"hits": sum(values), "evaluated": len(values),
                          "rate": sum(values) / len(values) if values else None}
    result["mean_text_tokens"] = mean(s["text_tokens"] for s in scores) if scores else 0
    return result


def retrieve_ranked(store, vector, tokenization, expected_records):
    """Mismo vector en cada colección; solo filtro público, sin pistas del benchmark."""
    result = store.query(vector, top_k=max(KS), filter_dict={"source_scope": "public"})
    ranked = []
    for key, text, metadata, distance in zip(result["ids"][0], result["documents"][0],
            result["metadatas"][0], result["distances"][0], strict=True):
        if metadata.get("source_scope") != "public":
            raise ValueError("El experimento solo admite documentos públicos")
        if record_digest(text, metadata) != expected_records.get(key):
            raise ValueError("Registro diferente del corpus verificado")
        ranked.append({"id": key, "text": text, "metadata": metadata,
                       "cosine_similarity": 1.0 - float(distance),
                       "text_tokens": tokenization.count(text, special_tokens=False)})
    return ranked


def evaluate(questions, stores, service, tokenization, records):
    """Vectoriza cada pregunta una vez y compara prefijos del mismo ranking top-8."""
    results = {name: [] for name in stores}
    for question in questions:
        vector = service.embed_query(question["question"])
        for name, store in stores.items():
            ranked = retrieve_ranked(store, vector, tokenization, records[name])
            results[name].append({"question": question, "ranked": ranked,
                "scores": {str(k): score_question(question, ranked, k) for k in KS}})
        print(f"Evaluada {question['id']}", flush=True)
    return {name: {"questions": rows, "summary": [summarize(rows, k) for k in KS]}
            for name, rows in results.items()}


def open_stores(manifest, settings):
    """Abre solo colecciones existentes con la configuración del servicio compartido."""
    from src.indexing.vectorstore import get_vectorstore

    stores = {}
    # Comprueba que existen antes de usar get_or_create del servicio compartido.
    import chromadb
    from chromadb.config import Settings as ChromaSettings
    client = chromadb.PersistentClient(path=settings.chroma_dir,
        settings=ChromaSettings(anonymized_telemetry=False))
    for name, records in manifest["collections"].items():
        collection = client.get_collection(name, embedding_function=None)
        if not records or collection.count() != len(records):
            raise ValueError(f"{name}: colección incompleta o modificada")
        stores[name] = get_vectorstore(settings.model_copy(update={"chroma_collection": name}))
    return stores


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--benchmark", type=Path, default=PROJECT_ROOT / "data/eval/benchmark.json")
    args = parser.parse_args()
    manifest_raw = args.manifest.read_bytes()
    manifest = json.loads(manifest_raw)
    if manifest["status"] != "verified" or not manifest["collections"]:
        raise ValueError("Se requiere una indexación completa y verificada")
    documents = {d["doc_id"]: d["pages"] for d in manifest["report"]["documents"]}
    questions, benchmark_hash = load_questions(args.benchmark, documents)

    from src.indexing.embeddings import EmbeddingService

    settings = Settings(_env_file=None, embedding_model=manifest["model"],
        embedding_max_tokens=manifest["report"]["max_input_tokens"],
        embedding_passage_prefix=manifest["report"]["passage_prefix"],
        chroma_dir=manifest["directory"])
    stores = open_stores(manifest, settings)
    tokenization = load_tokenization(settings)
    service = EmbeddingService(settings)
    results = evaluate(questions, stores, service, tokenization, manifest["collections"])
    report = {"created_at": datetime.now(timezone.utc).isoformat(),
        "manifest": str(args.manifest.resolve()), "manifest_sha256": sha256(manifest_raw).hexdigest(),
        "benchmark_sha256": benchmark_hash, "model": manifest["model"],
        "threshold": None, "ks": KS, "ranking": "Prefixes of one top-8 query per collection",
        "token_measure": "Sum of retrieved original-text tokens, excluding prompt/citations/special tokens",
        "limitations": ["Reference hits do not prove complete evidence or correct answers",
                        "No exhaustive relevance labels: these are not chunk Recall@k metrics",
                        "Special cases without references are recorded but not scored",
                        "No held-out test set; configuration selection requires content review"],
        "results": results}
    output = args.manifest.parent / "evaluations" / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    output.mkdir(parents=True)
    (output / "results.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    lines = ["# Comparación inicial de referencias", "",
             "| Colección | k | Documento | Página | Tokens medios de texto (40 preguntas) |",
             "|---|---:|---:|---:|---:|"]
    for name, result in results.items():
        for row in result["summary"]:
            doc, page = row["document_hit"], row["page_hit"]
            lines.append(f"| {name} | {row['k']} | {doc['hits']}/{doc['evaluated']} | "
                         f"{page['hits']}/{page['evaluated']} | {row['mean_text_tokens']:.1f} |")
    lines.extend(["", "No selecciona ganador: hace falta revisar la evidencia recuperada.",
                  "El detalle JSON conserva preguntas, notas y textos para esa revisión."])
    summary = "\n".join(lines) + "\n"
    (output / "summary.md").write_text(summary, encoding="utf-8")
    print(summary)
    print(f"Resultados: {output}")


if __name__ == "__main__":
    main()
