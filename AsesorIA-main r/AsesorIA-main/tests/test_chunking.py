"""Tests offline de tokens, offsets, metadatos y contexto de sección."""
from copy import deepcopy

import pytest

from src.common.schemas import ChunkMetadata
from src.common.tokenization import Tokenization
from src.ingestion.loaders import LoadedPage
from src.ingestion.chunking import (
    ChunkingConfig, SectionSpan, chunk_document, join_pages_with_spans, get_page_range,
)


class ByteTokenizer:
    """Doble de prueba: un token por byte UTF-8, más dos especiales.

    No representa E5. Permite probar que caracteres y tokens son distintos
    sin red; el test separado de E5 usa su tokenizer real.
    """
    model_max_length = 512

    def encode(self, text, *, add_special_tokens=True, truncation=False):
        assert truncation is False
        return ([0] if add_special_tokens else []) + list(text.encode("utf-8")) + ([1] if add_special_tokens else [])


@pytest.fixture
def metadata():
    return ChunkMetadata(doc_id="iva_2025", tax="IVA", doc_type="official_guide",
                         fiscal_year=2025, source_url="https://example.org/manual.pdf",
                         retrieved_at="2026-10-01", source_scope="public",
                         valid_from="2025-01-01")


@pytest.fixture
def tokenization():
    return Tokenization(ByteTokenizer(), 512, "passage: ")


@pytest.mark.parametrize("start,end,expected", [
    (0, 5, (7, 7)), (3, 8, (7, 8)), (3, 6, (7, 7)),
    (5, 8, (8, 8)), (6, 11, (8, 8)), (0, 11, (7, 8)),
])
def test_page_boundaries(start, end, expected):
    _, spans = join_pages_with_spans([LoadedPage("ABCDE", 7), LoadedPage("FGHIJ", 8)])
    assert get_page_range(start, end, spans) == expected


@pytest.mark.parametrize("start,end", [(5, 6), (-1, 2), (3, 3), (8, 3), (10, 12)])
def test_invalid_page_ranges(start, end):
    _, spans = join_pages_with_spans([LoadedPage("ABCDE", 7), LoadedPage("FGHIJ", 8)])
    with pytest.raises(ValueError):
        get_page_range(start, end, spans)


def test_empty_pages_and_separators():
    text, spans = join_pages_with_spans([
        LoadedPage("", 6), LoadedPage("ABCDE", 7), LoadedPage("", 8),
        LoadedPage("FGHIJ", 9), LoadedPage("", 10),
    ])
    assert get_page_range(0, len(text), spans) == (7, 9)
    with pytest.raises(ValueError):
        get_page_range(6, 8, spans)


@pytest.mark.parametrize("size,overlap", [(40, 0), (48, 8), (64, 16), (80, 32)])
def test_token_budget_offsets_and_coverage(metadata, tokenization, size, overlap):
    pages = [LoadedPage("IVA: deducción, autónomo. " * 12, 7),
             LoadedPage("IVA: deducción, autónomo. " * 12, 8)]
    original = deepcopy(metadata.model_dump())
    text, spans = join_pages_with_spans(pages)
    chunks = chunk_document(pages, metadata, config=ChunkingConfig(size, overlap), tokenization=tokenization)
    covered = set()
    for i, chunk in enumerate(chunks):
        assert chunk.text == text[chunk.start:chunk.end]
        assert chunk.token_count == tokenization.count(chunk.embedding_text) <= size
        assert chunk.overlap_tokens <= overlap
        assert (chunk.metadata.page, chunk.metadata.page_end) == get_page_range(chunk.start, chunk.end, spans)
        assert chunk.metadata.chunk_index == i
        assert chunk.metadata.doc_id == metadata.doc_id
        assert chunk.metadata.valid_from == metadata.valid_from
        assert chunk.metadata.source_url == metadata.source_url
        covered.update(range(chunk.start, chunk.end))
    assert all(i in covered for i, c in enumerate(text) if not c.isspace())
    assert metadata.model_dump() == original
    assert all(a.start < b.start and a.end < b.end for a, b in zip(chunks, chunks[1:]))


def test_title_budget_and_inheritance(metadata, tokenization):
    text = "Gastos deducibles. " * 30
    section = SectionSpan(0, len(text), "Gastos", "IRPF > Gastos")
    chunks = chunk_document([LoadedPage(text, 3)], metadata,
                            config=ChunkingConfig(70, 12), tokenization=tokenization,
                            sections=[section])
    assert len(chunks) > 1
    for c in chunks:
        assert c.metadata.section_label == "Gastos"
        assert c.metadata.section_path == "IRPF > Gastos"
        assert c.embedding_text.startswith("passage: IRPF > Gastos\nGastos\n\n")
        assert c.token_count <= 70
        assert c.text == text[c.start:c.end]


def test_section_local_positions_are_not_confused_with_document(metadata, tokenization):
    pages = [LoadedPage("Introducción\nABC", 7), LoadedPage("DEF", 8)]
    text, _ = join_pages_with_spans(pages)
    start = text.index("ABC")
    chunks = chunk_document(pages, metadata, config=ChunkingConfig(100, 0),
                            tokenization=tokenization,
                            sections=[SectionSpan(start, len(text), "Apartado", "Apartado")])
    assert chunks[-1].start == start
    assert chunks[-1].text == "ABC\nDEF"
    assert (chunks[-1].metadata.page, chunks[-1].metadata.page_end) == (7, 8)
    assert chunks[0].text == "Introducción"  # El hueco no desaparece.


def test_markdown_is_opt_in_and_respects_fenced_code(metadata, tokenization):
    text = "Intro\n# IVA\nContenido\n```python\n# falso\n```\n## Deducciones\nDetalle\n# IRPF\nFinal"
    config = ChunkingConfig(180, 20, detect_markdown_headings=True)
    chunks = chunk_document([LoadedPage(text, 1)], metadata, config=config, tokenization=tokenization)
    assert [c.metadata.section_label for c in chunks] == ["", "IVA", "Deducciones", "IRPF"]
    assert chunks[2].metadata.section_path == "IVA > Deducciones"
    assert all(c.overlap_tokens == 0 for c in chunks)  # No cruza secciones.
    fallback = chunk_document([LoadedPage(text, 1)], metadata,
                              config=ChunkingConfig(180, 20), tokenization=tokenization)
    assert all(c.metadata.section_label == "" for c in fallback)


def test_no_guessing_pdf_titles(metadata, tokenization):
    text = "GASTOS DEDUCIBLES\nTexto fiscal.\n1. Un apartado posible"
    chunks = chunk_document([LoadedPage(text, 1)], metadata,
                            config=ChunkingConfig(180, 20), tokenization=tokenization)
    assert all(c.metadata.section_label == "" for c in chunks)


def test_metadata_is_inherited_including_private_scope(metadata, tokenization):
    metadata = metadata.model_copy(update={"source_scope": "private", "session_id": "session-a",
                                          "section_label": "Título", "section_path": "Capítulo"})
    chunk = chunk_document([LoadedPage("Contenido", 4)], metadata,
                           config=ChunkingConfig(128, 12), tokenization=tokenization)[0]
    assert chunk.metadata.session_id == "session-a"
    assert chunk.metadata.source_scope == "private"
    assert chunk.metadata.section_label == "Título"
    assert chunk.metadata.page_end == chunk.metadata.page == 4


def test_private_input_needs_session(metadata, tokenization):
    with pytest.raises(ValueError, match="session_id"):
        chunk_document([LoadedPage("texto", 1)], metadata.model_copy(update={"source_scope": "private"}),
                       config=ChunkingConfig(64, 8), tokenization=tokenization)


@pytest.mark.parametrize("text", ["", " \n\t "])
def test_blank_input(text, metadata, tokenization):
    assert chunk_document([LoadedPage(text, 1)], metadata, config=ChunkingConfig(64, 8),
                          tokenization=tokenization) == []


def test_final_cut_preserves_unicode(metadata, tokenization):
    text = "á漢🙂" * 40
    chunks = chunk_document([LoadedPage(text, 1)], metadata,
                            config=ChunkingConfig(32, 0), tokenization=tokenization)
    assert "".join(c.text for c in chunks) == text
    assert all(c.token_count <= 32 for c in chunks)


def test_context_too_large_is_not_silently_truncated(metadata, tokenization):
    with pytest.raises(ValueError, match="contexto"):
        chunk_document([LoadedPage("Texto", 1)], metadata,
                       config=ChunkingConfig(32, 0), tokenization=tokenization,
                       sections=[SectionSpan(0, 5, "Título" * 20)])


def test_model_limit_is_enforced(metadata, tokenization):
    with pytest.raises(ValueError, match="límite"):
        chunk_document([], metadata, config=ChunkingConfig(513, 32), tokenization=tokenization)


@pytest.mark.parametrize("size,overlap,error", [(0, 0, ValueError), (32, -1, ValueError),
    (32, 32, ValueError), (True, 0, TypeError), (32, 1.5, TypeError)])
def test_config_validation(size, overlap, error):
    with pytest.raises(error):
        ChunkingConfig(size, overlap)


@pytest.mark.parametrize("sections", [
    [SectionSpan(0, 20)], [SectionSpan(-1, 2)],
    [SectionSpan(0, 4), SectionSpan(3, 5)], [SectionSpan(0, 0)],
])
def test_invalid_sections(sections, metadata, tokenization):
    with pytest.raises(ValueError):
        chunk_document([LoadedPage("abcde", 1)], metadata,
                       config=ChunkingConfig(64, 8), tokenization=tokenization, sections=sections)


def test_counting_combined_text_not_sum_of_pieces(metadata):
    class ContextSensitiveTokenizer(ByteTokenizer):
        def encode(self, text, **kwargs):
            # Deliberately non-additive at concatenation boundaries.
            return super().encode(text.replace("a b", "X"), **kwargs)
    profile = Tokenization(ContextSensitiveTokenizer(), 512)
    chunks = chunk_document([LoadedPage("a b " * 30, 1)], metadata,
                            config=ChunkingConfig(12, 2), tokenization=profile)
    assert all(c.token_count == profile.count(c.embedding_text) <= 12 for c in chunks)
