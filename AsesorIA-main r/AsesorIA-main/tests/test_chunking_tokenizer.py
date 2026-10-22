"""Integración opcional: descarga SOLO tokenizer E5, nunca pesos del modelo.

RUN_TOKENIZER_INTEGRATION=1 uv run ... pytest tests/test_chunking_tokenizer.py
"""
import os

import pytest

from src.common.schemas import ChunkMetadata
from src.common.settings import Settings
from src.common.tokenization import load_tokenization
from src.ingestion.loaders import LoadedPage
from src.ingestion.chunking import ChunkingConfig, SectionSpan, chunk_document, join_pages_with_spans

pytestmark = pytest.mark.skipif(os.environ.get("RUN_TOKENIZER_INTEGRATION") != "1",
                                reason="Activa RUN_TOKENIZER_INTEGRATION=1 para usar el tokenizer real")


@pytest.fixture(scope="module")
def e5():
    return load_tokenization(Settings(_env_file=None, embedding_model="intfloat/multilingual-e5-base",
                                     embedding_passage_prefix="passage: "))


@pytest.mark.parametrize("size,overlap", [(256, 32), (384, 48), (480, 64)])
def test_real_e5_budgets_and_provenance(e5, size, overlap):
    body = "Los gastos deducibles requieren justificación documental. IVA, IRPF y cotización. " * 35
    pages = [LoadedPage(body, 7), LoadedPage(body, 8)]
    text, _ = join_pages_with_spans(pages)
    metadata = ChunkMetadata(doc_id="synthetic-fixture", doc_type="official_guide", source_scope="public")
    chunks = chunk_document(pages, metadata, config=ChunkingConfig(size, overlap), tokenization=e5,
                            sections=[SectionSpan(0, len(text), "Gastos deducibles", "IRPF > Gastos")])
    assert len(chunks) > 1
    covered = set()
    for chunk in chunks:
        assert chunk.token_count == e5.count(chunk.embedding_text) <= size
        assert chunk.text == text[chunk.start:chunk.end]
        assert chunk.overlap_tokens <= overlap
        assert chunk.metadata.section_label == "Gastos deducibles"
        covered.update(range(chunk.start, chunk.end))
    assert all(i in covered for i, char in enumerate(text) if not char.isspace())
    assert chunks[0].metadata.page == 7
    assert chunks[-1].metadata.page_end == 8
