import argparse
import csv
import math
import subprocess
import sys
from pathlib import Path
from uuid import uuid4
import json
from datetime import datetime, timezone
from hashlib import sha256

from src.common.schemas import ChunkMetadata
from src.common.tokenization import load_tokenization
from src.ingestion.chunking import (
    ChunkingConfig, chunk_document, join_pages_with_spans, get_page_range,
)

from src.common.settings import PROJECT_ROOT, Settings, get_settings
from src.ingestion.loaders import load_document, LoadedPage
from src.ingestion.cleaning import clean_text, remove_repeated_lines


def check_corpus():
    """Comprueba que cada PDF del catálogo existe y no está vacío."""
    catalog_path = PROJECT_ROOT / "data" / "sources.csv"
    raw_dir = PROJECT_ROOT / "data" / "raw"

    with catalog_path.open(encoding="utf-8-sig", newline="") as file:
        sources = list(csv.DictReader(file))

    if not sources:
        raise ValueError("El catálogo de documentos está vacío")

    missing = []

    for source in sources:
        path = raw_dir / source["filename"]

        if not path.is_file() or path.stat().st_size == 0:
            missing.append(source["filename"])
            print(f"FALTA O ESTÁ VACÍO: {source['filename']}")
        else:
            print(f"OK: {source['doc_id']} → {source['filename']}")

    if missing:
        raise FileNotFoundError(
            f"Hay {len(missing)} documentos ausentes o vacíos"
        )

    print(f"\nCatálogo comprobado: {len(sources)} documentos.")
    return sources


def load_clean_pages(source):
    """Carga un documento del catálogo y conserva la numeración de sus páginas."""
    path = PROJECT_ROOT / "data" / "raw" / source["filename"]
    pages = load_document(path)

    # Política auditada para los PDF actuales; revisar si cambia el corpus.
    # En los manuales AEAT conservamos las viñetas: solo clean_text.
    if source["tax"] == "RETA":
        pages = remove_repeated_lines(pages)

    return [
        LoadedPage(text=clean_text(page.text), page=page.page)
        for page in pages
    ]


# Candidatas experimentales; ninguna se considera ganadora todavía.
CONFIGURATIONS = ((256, 32), (384, 48), (480, 64))


def validate_chunks(chunks, pages, metadata, config, tokenization):
    """Comprueba límites, procedencia y cobertura sin generar vectores."""
    text, spans = join_pages_with_spans(pages)
    if not text.strip() or not chunks:
        raise ValueError(f"{metadata.doc_id}: documento sin texto útil o sin chunks")
    covered_until = 0
    previous_start = -1
    counts = []
    for index, chunk in enumerate(chunks):
        def require(condition, message):
            if not condition:
                raise ValueError(f"{metadata.doc_id}, chunk {index}: {message}")

        require(0 <= chunk.start < chunk.end <= len(text), "offsets inválidos")
        require(chunk.start >= previous_start, "fragmentos desordenados")
        require(chunk.text == text[chunk.start:chunk.end], "texto original alterado")
        require(bool(chunk.text.strip()), "fragmento vacío")
        require(not text[covered_until:chunk.start].strip(), "texto sin cubrir")
        expected_pages = get_page_range(chunk.start, chunk.end, spans)
        require((chunk.metadata.page, chunk.metadata.page_end) == expected_pages,
                "rango de páginas incorrecto")
        expected_metadata = metadata.model_dump()
        expected_metadata.update(page=expected_pages[0], page_end=expected_pages[1],
                                 chunk_index=index)
        require(chunk.metadata.model_dump() == expected_metadata, "metadata alterada")
        expected_embedding_text = tokenization.prepare(
            chunk.text, chunk.metadata.section_label, chunk.metadata.section_path
        )
        require(chunk.embedding_text == expected_embedding_text, "contexto incorrecto")
        count = tokenization.count(chunk.embedding_text)
        require(count == chunk.token_count, "conteo de tokens incorrecto")
        require(count <= min(config.max_tokens, tokenization.max_input_tokens),
                "presupuesto de tokens superado")
        require(0 <= chunk.overlap_tokens <= config.overlap_tokens,
                "overlap fuera del presupuesto")
        counts.append(count)
        covered_until = max(covered_until, chunk.end)
        previous_start = chunk.start

    if text[covered_until:].strip():
        raise ValueError(f"{metadata.doc_id}: texto final sin cubrir")
    return {
        "chunks": len(chunks),
        "min_tokens": min(counts, default=0),
        "max_tokens": max(counts, default=0),
        "max_overlap_tokens": max((c.overlap_tokens for c in chunks), default=0),
        "cross_page_chunks": sum(c.metadata.page != c.metadata.page_end for c in chunks),
    }


def record_digest(text, metadata):
    """Huella de texto y metadata para verificar disco sin duplicar el corpus."""
    return sha256(json.dumps([text, metadata], sort_keys=True,
                             ensure_ascii=False).encode("utf-8")).hexdigest()


def index_chunks(store, chunks, *, batch_size=128):
    """Lotes pequeños permiten ver progreso; el servicio reutiliza el modelo."""
    if type(batch_size) is not int or batch_size <= 0:
        raise ValueError("batch_size debe ser positivo")
    records = {}
    for start in range(0, len(chunks), batch_size):
        batch = chunks[start:start + batch_size]
        ids = store.add_chunks(batch)
        for key, chunk in zip(ids, batch, strict=True):
            records[key] = record_digest(chunk.text, chunk.metadata.to_store_dict())
        print(f"    Guardados {min(start + batch_size, len(chunks))}/{len(chunks)}",
              flush=True)
    return records


def verify_saved(manifest_path):
    """Reabre colecciones sin cargar E5; verifica todos los registros y consulta."""
    from src.indexing.vectorstore import get_vectorstore

    manifest = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
    if manifest["status"] not in ("indexed", "verified"):
        raise ValueError("La indexación está incompleta")
    collections = manifest["collections"]
    if not collections or any(not records for records in collections.values()):
        raise ValueError("El manifiesto no puede contener colecciones vacías")
    for name, expected in collections.items():
        store = get_vectorstore(Settings(_env_file=None,
            chroma_dir=manifest["directory"], chroma_collection=name))
        if store.collection.count() != len(expected):
            raise ValueError(f"{name}: recuento incorrecto")
        keys = list(expected)
        dimensions = len(manifest["query_vector"])
        for offset in range(0, len(keys), 128):
            batch = keys[offset:offset + 128]
            saved = store.collection.get(ids=batch,
                include=["documents", "metadatas", "embeddings"])
            if set(saved["ids"]) != set(batch):
                raise ValueError("Faltan IDs persistidos")
            for key, text, metadata, vector in zip(saved["ids"], saved["documents"],
                    saved["metadatas"], saved["embeddings"], strict=True):
                if record_digest(text, metadata) != expected[key]:
                    raise ValueError("Texto o metadata persistidos alterados")
                if (len(vector) != dimensions or
                    not all(math.isfinite(float(x)) for x in vector) or
                    not math.isclose(sum(float(x)**2 for x in vector), 1, abs_tol=1e-5)):
                    raise ValueError("Vector inválido o sin normalizar")
        result = store.query(manifest["query_vector"], top_k=4,
                             filter_dict={"source_scope": "public"})
        if len(result["ids"][0]) != min(4, len(expected)):
            raise ValueError("Búsqueda tras reapertura incorrecta")
        for key, text, metadata in zip(result["ids"][0], result["documents"][0],
                                       result["metadatas"][0], strict=True):
            if record_digest(text, metadata) != expected.get(key):
                raise ValueError("Documento recuperado diferente del original")
        print(f"Reapertura y búsqueda correctas: {name} ({len(expected)} chunks)", flush=True)


def save_manifest(path, manifest):
    """Publica el estado después de cada documento/configuración completado."""
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(path)


def validate_storage_path(directory):
    """Chroma 1.5.9/HNSW no persiste correctamente rutas no ASCII en Windows."""
    path = Path(directory).resolve()
    if sys.platform == "win32" and not str(path).isascii():
        raise ValueError(
            "Chroma en Windows requiere aquí una ruta sin acentos para persistir HNSW. "
            "Configura CHROMA_DIR con una ruta ASCII antes de indexar."
        )
    return path


def main(argv=None):
    parser = argparse.ArgumentParser(description="Comprueba o indexa el corpus completo")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--index", action="store_true", help="Genera embeddings y persiste las tres configuraciones")
    mode.add_argument("--verify", type=Path, help="Comprueba un manifiesto en un proceso nuevo, sin E5")
    args = parser.parse_args(argv)
    if args.verify:
        verify_saved(args.verify)
        return
    sources = check_corpus()
    settings = get_settings()
    if args.index:
        validate_storage_path(settings.chroma_dir)
    tokenization = load_tokenization(settings)
    stores = {}
    manifest = None
    if args.index:
        from src.indexing.embeddings import EmbeddingService
        from src.indexing.vectorstore import get_vectorstore

        service = EmbeddingService(settings)
        directory = Path(settings.chroma_dir).resolve() / "corpus_runs" / uuid4().hex
        directory.mkdir(parents=True)
        manifest_path = directory / "manifest.json"
        manifest = {"status": "in_progress", "directory": str(directory),
                    "model": settings.embedding_model, "collections": {},
                    "question": "¿Qué obligaciones fiscales tiene una persona autónoma?"}
        manifest["query_vector"] = service.embed_query(manifest["question"])
        for size, overlap in CONFIGURATIONS:
            name = f"corpus_{size}_{overlap}"
            stores[f"{size}/{overlap}"] = get_vectorstore(settings.model_copy(update={
                "chroma_dir": str(directory), "chroma_collection": name}),
                embedding_service=service)
            manifest["collections"][name] = {}
        save_manifest(manifest_path, manifest)
    report = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "tokenizer": tokenization.tokenizer.name_or_path,
        "max_input_tokens": tokenization.max_input_tokens,
        "passage_prefix": tokenization.passage_prefix,
        "cleaning": "RETA: remove_repeated_lines + clean_text; AEAT: clean_text",
        "sections": "No inferred headings; shared chunking defaults",
        "documents": [],
        "totals": {f"{size}/{overlap}": 0 for size, overlap in CONFIGURATIONS},
    }
    for source in sources:
        print(f"\nLeyendo {source['doc_id']}...", flush=True)
        pages = load_clean_pages(source)
        metadata = ChunkMetadata(
            **{key: value for key, value in source.items() if key != "filename"},
            source_scope="public",
        )
        path = PROJECT_ROOT / "data" / "raw" / source["filename"]
        document = {
            "doc_id": metadata.doc_id,
            "filename": source["filename"],
            "sha256": sha256(path.read_bytes()).hexdigest(),
            "pages": len(pages),
            "empty_pages": sum(not page.text.strip() for page in pages),
            "configurations": {},
        }
        print(f"Páginas: {len(pages)} | Vacías: {document['empty_pages']}", flush=True)
        for size, overlap in CONFIGURATIONS:
            key = f"{size}/{overlap}"
            print(f"  Dividiendo y validando {key}...", flush=True)
            config = ChunkingConfig(size, overlap)
            chunks = chunk_document(pages, metadata, config=config,
                                    tokenization=tokenization)
            stats = validate_chunks(chunks, pages, metadata, config, tokenization)
            document["configurations"][key] = stats
            report["totals"][key] += stats["chunks"]
            print(f"  {key}: {stats}", flush=True)
            if args.index:
                store = stores[key]
                manifest["collections"][store.collection.name].update(index_chunks(store, chunks))
                save_manifest(manifest_path, manifest)
            del chunks
        report["documents"].append(document)

    if args.index:
        manifest.update(status="indexed", report=report)
        save_manifest(manifest_path, manifest)
        subprocess.run([sys.executable, "-m", "scripts.index_corpus", "--verify",
                        str(manifest_path)], cwd=PROJECT_ROOT, check=True)
        manifest["status"] = "verified"
        save_manifest(manifest_path, manifest)
        print(f"Colecciones verificadas. Manifiesto: {manifest_path}", flush=True)

    # Informe de recuentos; las colecciones solo se crean con --index.
    output = PROJECT_ROOT / "chroma_db" / "corpus_chunking_check.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nTotales de chunks: {report['totals']}")
    print(f"Informe: {output}")
    print("Validación técnica; no mide calidad del retrieval ni elige parámetros óptimos.")


if __name__ == "__main__":
    main()
