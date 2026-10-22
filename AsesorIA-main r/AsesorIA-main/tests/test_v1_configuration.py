"""Defaults de V1 compartidos, sin descargar modelos ni llamar a APIs."""
from unittest.mock import Mock
import pytest
from src.common.settings import Settings
from src.ingestion.chunking import ChunkingConfig
from src.retrieval.retriever import get_retriever
from src.rag import engine


def test_chunking_v1_and_explicit_override():
    settings = Settings(_env_file=None, chunk_size_tokens=256, chunk_overlap_tokens=32)
    assert ChunkingConfig.from_settings(settings) == ChunkingConfig(256, 32)
    assert ChunkingConfig.from_settings(settings.model_copy(update={
        "chunk_size_tokens": 384, "chunk_overlap_tokens": 48})) == ChunkingConfig(384, 48)
    assert Settings.model_fields["chroma_collection"].default == "corpus_256_32"
    assert Settings.model_fields["chunk_size_tokens"].default == 256
    assert Settings.model_fields["chunk_overlap_tokens"].default == 32


@pytest.mark.parametrize("factory", [engine.RAGEngine, engine.get_rag_engine])
def test_engine_uses_v1_retriever_and_allows_disabled_threshold(monkeypatch, factory):
    store = Mock()
    store.query.return_value = {
        "documents": [["evidencia", "ruido"]],
        "metadatas": [[{"source_scope": "public", "doc_id": "a"},
                       {"source_scope": "public", "doc_id": "b"}]],
        "distances": [[0.17, 0.19]],
    }
    monkeypatch.setattr(engine, "get_retriever", lambda **kw: get_retriever(vectorstore=store, **kw))
    monkeypatch.setattr(engine, "get_llm", lambda: object())
    monkeypatch.setattr(engine, "RAGPipeline", lambda retriever, llm: Mock(retriever=retriever))
    monkeypatch.setattr(engine, "_engine_instance", None)
    r = factory().pipeline.retriever
    assert [d.page_content for d in r.invoke("pregunta")] == ["evidencia"]
    assert store.query.call_args.kwargs["top_k"] == 8
    monkeypatch.setattr(engine, "_engine_instance", None)
    r = factory(top_k=3, score_threshold=None).pipeline.retriever
    assert len(r.invoke("pregunta")) == 2
    assert store.query.call_args.kwargs["top_k"] == 3
