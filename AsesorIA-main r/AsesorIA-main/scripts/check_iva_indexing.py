"""Prueba técnica real de páginas 40–42 del IVA; no evalúa calidad del retrieval.

Ejecutar: python -m scripts.check_iva_indexing
Prueba 256/32, 384/48 y 480/64. Cada configuración crea su propia colección en chroma_db/iva_smoke/ (fuera de Git).
"""
from pathlib import Path
import csv
import json
import math
import subprocess
import sys
from uuid import uuid4

from src.common.settings import PROJECT_ROOT, Settings
from src.common.schemas import ChunkMetadata
from src.common.tokenization import load_tokenization
from src.ingestion.loaders import load_document, LoadedPage
from src.ingestion.cleaning import clean_text
from src.ingestion.chunking import chunk_document, ChunkingConfig, join_pages_with_spans, get_page_range
from src.indexing.embeddings import EmbeddingService
from src.indexing.vectorstore import get_vectorstore
from src.retrieval.retriever import get_retriever


def verify_saved(manifest_path: Path):
    """Un proceso nuevo comprueba disco sin generar embeddings otra vez."""
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    settings = Settings(_env_file=None, chroma_dir=manifest['directory'],
                        chroma_collection=manifest['collection'])
    store = get_vectorstore(settings)
    assert store.collection.count() == len(manifest['chunks'])
    assert store.collection.configuration['hnsw']['space'] == 'cosine'
    saved = store.collection.get(include=['documents', 'metadatas', 'embeddings'])
    expected = {chunk['id']: chunk for chunk in manifest['chunks']}
    for chunk_id, text, metadata, vector in zip(saved['ids'], saved['documents'],
                                               saved['metadatas'], saved['embeddings'], strict=True):
        assert text == expected[chunk_id]['text'], 'Texto original alterado'
        assert metadata == expected[chunk_id]['metadata'], 'Metadatos alterados'
        assert len(vector) == 768
        assert all(math.isfinite(float(value)) for value in vector)
        assert math.isclose(math.sqrt(sum(float(x) ** 2 for x in vector)), 1, abs_tol=1e-5)
    result = store.query(manifest['query_vector'], top_k=4,
                         filter_dict={'source_scope': 'public'})
    assert len(result['documents'][0]) == min(4, len(expected))
    print('Reapertura en otro proceso: texto, metadatos, vectores y búsqueda correctos.', flush=True)


def main():
    with (PROJECT_ROOT / 'data/sources.csv').open(encoding='utf-8-sig', newline='') as file:
        source = next(row for row in csv.DictReader(file) if row['doc_id'] == 'iva_manual_2025')
    metadata = ChunkMetadata(**{k: v for k, v in source.items() if k != 'filename'}, source_scope='public')
    pages = load_document(PROJECT_ROOT / 'data/raw' / source['filename'])
    # Para este experimento no eliminamos líneas repetidas: borraban las viñetas.
    sample = [LoadedPage(clean_text(page.text), page.page) for page in pages[39:42]]
    assert len(sample) == 3
    settings = Settings(_env_file=None, embedding_model='intfloat/multilingual-e5-base',
                        embedding_passage_prefix='passage: ',
                        chroma_dir=str(PROJECT_ROOT / 'chroma_db' / 'iva_smoke'),
                        chroma_collection='iva_smoke_' + uuid4().hex)
    tokenization = load_tokenization(settings)
    # Un modelo compartido para las tres configuraciones, sin recargar pesos.
    service = EmbeddingService(settings)
    run_id = uuid4().hex
    summaries = []
    for size, overlap in [(256, 32), (384, 48), (480, 64)]:
        settings = settings.model_copy(update={
            'chroma_collection': f'iva_smoke_{size}_{overlap}_{run_id}'})
        print(f'\n=== Configuración {size}/{overlap} ===', flush=True)
        chunks = chunk_document(sample, metadata, config=ChunkingConfig(size, overlap), tokenization=tokenization)
        text, spans = join_pages_with_spans(sample)
        covered = set()
        for chunk in chunks:
            assert chunk.text == text[chunk.start:chunk.end]
            assert chunk.token_count == tokenization.count(chunk.embedding_text) <= size
            assert chunk.overlap_tokens <= overlap
            assert (chunk.metadata.page, chunk.metadata.page_end) == get_page_range(chunk.start, chunk.end, spans)
            covered.update(range(chunk.start, chunk.end))
            print(f'Chunk {chunk.metadata.chunk_index}: páginas {chunk.metadata.page}-{chunk.metadata.page_end}, '
                  f'{chunk.token_count} tokens; overlap {chunk.overlap_tokens}', flush=True)
        assert all(i in covered for i, char in enumerate(text) if not char.isspace())
        print('Generando embeddings e indexando...', flush=True)
        store = get_vectorstore(settings, embedding_service=service)
        # add_chunks usa embedding_text para el vector y text para el documento.
        ids = store.add_chunks(chunks)
        assert store.collection.count() == len(chunks)
        question = '¿Dónde se consideran realizadas las ventas a distancia intracomunitarias?'
        retriever = get_retriever(top_k=4, score_threshold=None, vectorstore=store)
        documents = retriever.invoke(question)
        assert len(documents) == min(4, len(chunks))
        by_index = {chunk.metadata.chunk_index: chunk for chunk in chunks}
        for doc in documents:
            chunk = by_index[doc.metadata['chunk_index']]
            assert doc.page_content == chunk.text
            assert doc.metadata == dict(chunk.metadata.to_store_dict(), source=chunk.metadata.source_url)
            print(f"Recuperado chunk {doc.metadata['chunk_index']}, páginas "
                  f"{doc.metadata['page']}-{doc.metadata['page_end']}: {doc.page_content[:160]}", flush=True)
        # Vector de comprobación para que el proceso lector no cargue otro modelo.
        query_vector = service.embed_query(question)
        manifest_path = Path(settings.chroma_dir) / (settings.chroma_collection + '.json')
        manifest = dict(directory=settings.chroma_dir, collection=settings.chroma_collection,
                        model=settings.embedding_model, pages=[40, 42], chunk_size=size, overlap=overlap,
                        cleaning='clean_text only; preserve bullet lines', top_k=4, threshold=None,
                        question=question, query_vector=query_vector,
                        retrieved=[dict(text=doc.page_content, metadata=doc.metadata) for doc in documents],
                        chunks=[dict(id=key, text=chunk.text, metadata=chunk.metadata.to_store_dict())
                                for key, chunk in zip(ids, chunks, strict=True)])
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
        subprocess.run([sys.executable, '-m', 'scripts.check_iva_indexing', '--verify', str(manifest_path)],
                       cwd=PROJECT_ROOT, check=True, timeout=120)
        print(f'OK: {len(chunks)} chunks, vectores de 768 dimensiones normalizados, '
              f'{len(documents)} documentos recuperados.', flush=True)
        print('Registro de la prueba:', manifest_path, flush=True)
        summaries.append(dict(chunk_size=size, overlap=overlap, chunks=len(chunks),
                              min_tokens=min(c.token_count for c in chunks),
                              max_tokens=max(c.token_count for c in chunks),
                              max_overlap=max(c.overlap_tokens for c in chunks),
                              cross_page=sum(c.metadata.page != c.metadata.page_end for c in chunks),
                              retrieved=len(documents), manifest=str(manifest_path), verified=True))
    print('\nConfiguración | Chunks | Tokens min-max | Overlap máximo | Cruzan página | Recuperados')
    for row in summaries:
        print(f"{row['chunk_size']}/{row['overlap']} | {row['chunks']} | "
              f"{row['min_tokens']}-{row['max_tokens']} | {row['max_overlap']} | "
              f"{row['cross_page']} | {row['retrieved']}")
    summary_path = Path(settings.chroma_dir) / f'comparison_{run_id}.json'
    summary_path.write_text(json.dumps(summaries, ensure_ascii=False, indent=2), encoding='utf-8')
    print('Comparación guardada:', summary_path)
    print('Resultado técnico de una muestra; no mide Hit@k/Recall@k ni valida parámetros óptimos.')


if __name__ == '__main__':
    if len(sys.argv) == 3 and sys.argv[1] == '--verify':
        verify_saved(Path(sys.argv[2]))
    else:
        main()
