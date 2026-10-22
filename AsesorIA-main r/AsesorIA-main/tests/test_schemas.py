"""Tests for shared schema contracts."""

import pytest
from pydantic import ValidationError

pytest.importorskip("pydantic")

from src.common.schemas import (
    AnswerStatus,
    AskRequest,
    ChunkMetadata,
    DocType,
    IngestReport,
    RagAnswer,
    RetrievedChunk,
    RetrievalResult,
    Scope,
    Source,
    Tax,
)


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


def test_doc_type_values_are_stable():
    assert {item.value for item in DocType} == {
        "official_guide",
        "faq",
        "law",
        "user_upload",
    }


def test_scope_values_are_stable():
    assert {item.value for item in Scope} == {
        "public",
        "private",
    }


def test_tax_values_are_stable():
    assert {item.value for item in Tax} == {
        "IRPF",
        "IVA",
        "RETA",
        "GENERAL",
    }


def test_answer_status_values_are_stable():
    assert {item.value for item in AnswerStatus} == {
        "answered",
        "no_context",
        "out_of_scope",
        "year_unavailable",
        "error",
    }


# ---------------------------------------------------------------------------
# ChunkMetadata
# ---------------------------------------------------------------------------


def test_chunk_metadata_public_serializes_without_session_id():
    metadata = ChunkMetadata(
        doc_id="doc-public",
        doc_type=DocType.FAQ,
        source_scope=Scope.PUBLIC,
    )

    stored = metadata.to_store_dict()

    assert stored == {
        "doc_id": "doc-public",
        "tax": Tax.GENERAL.value,
        "doc_type": DocType.FAQ.value,
        "fiscal_year": 0,
        "valid_from": "",
        "valid_to": "",
        "section_label": "",
        "section_path": "",
        "page": 0,
        "page_end": 0,
        "source_url": "",
        "retrieved_at": "",
        "source_scope": Scope.PUBLIC.value,
        "chunk_index": 0,
    }


def test_chunk_metadata_private_preserves_session_id():
    metadata = ChunkMetadata(
        doc_id="doc-private",
        doc_type=DocType.FAQ,
        source_scope=Scope.PRIVATE,
        session_id="session-a",
    )

    stored = metadata.to_store_dict()

    assert stored["session_id"] == "session-a"
    assert stored["source_scope"] == Scope.PRIVATE.value


def test_chunk_metadata_drops_none_values():
    metadata = ChunkMetadata(
        doc_id="doc-public",
        doc_type=DocType.FAQ,
        source_scope=Scope.PUBLIC,
    )

    stored = metadata.to_store_dict()

    assert all(value is not None for value in stored.values())
    assert "session_id" not in stored


def test_chunk_metadata_defaults_are_applied():
    metadata = ChunkMetadata(
        doc_id="doc-1",
        doc_type=DocType.LAW,
        source_scope=Scope.PUBLIC,
    )

    assert metadata.tax == Tax.GENERAL.value
    assert metadata.fiscal_year == 0
    assert metadata.valid_from == ""
    assert metadata.valid_to == ""
    assert metadata.section_label == ""
    assert metadata.section_path == ""
    assert metadata.page == 0
    assert metadata.page_end == 0
    assert metadata.source_url == ""
    assert metadata.retrieved_at == ""
    assert metadata.session_id is None
    assert metadata.chunk_index == 0


def test_chunk_metadata_accepts_explicit_values():
    metadata = ChunkMetadata(
        doc_id="doc-2026",
        tax=Tax.IVA,
        doc_type=DocType.OFFICIAL_GUIDE,
        fiscal_year=2026,
        valid_from="2026-01-01",
        valid_to="2026-12-31",
        section_label="IVA reducido",
        section_path="IVA > Tipos > Reducido",
        page=12,
        page_end=14,
        source_url="https://example.com/source",
        retrieved_at="2026-10-06T10:00:00Z",
        source_scope=Scope.PUBLIC,
        chunk_index=7,
    )

    assert metadata.doc_id == "doc-2026"
    assert metadata.tax == Tax.IVA.value
    assert metadata.doc_type == DocType.OFFICIAL_GUIDE.value
    assert metadata.fiscal_year == 2026
    assert metadata.valid_from == "2026-01-01"
    assert metadata.valid_to == "2026-12-31"
    assert metadata.section_label == "IVA reducido"
    assert metadata.section_path == "IVA > Tipos > Reducido"
    assert metadata.page == 12
    assert metadata.page_end == 14
    assert metadata.source_url == "https://example.com/source"
    assert metadata.retrieved_at == "2026-10-06T10:00:00Z"
    assert metadata.source_scope == Scope.PUBLIC.value
    assert metadata.session_id is None
    assert metadata.chunk_index == 7


def test_chunk_metadata_to_store_dict_does_not_mutate_model():
    metadata = ChunkMetadata(
        doc_id="doc-private",
        doc_type=DocType.FAQ,
        source_scope=Scope.PRIVATE,
        session_id="session-123",
    )

    before = metadata.model_dump()
    metadata.to_store_dict()
    after = metadata.model_dump()

    assert after == before


def test_chunk_metadata_requires_doc_id():
    with pytest.raises(ValidationError):
        ChunkMetadata(
            doc_type=DocType.FAQ,
            source_scope=Scope.PUBLIC,
        )


def test_chunk_metadata_requires_doc_type():
    with pytest.raises(ValidationError):
        ChunkMetadata(
            doc_id="doc-1",
            source_scope=Scope.PUBLIC,
        )


def test_chunk_metadata_requires_source_scope():
    with pytest.raises(ValidationError):
        ChunkMetadata(
            doc_id="doc-1",
            doc_type=DocType.FAQ,
        )


# ---------------------------------------------------------------------------
# RetrievedChunk
# ---------------------------------------------------------------------------


def test_retrieved_chunk_contains_text_metadata_and_score():
    metadata = ChunkMetadata(
        doc_id="doc-1",
        doc_type=DocType.FAQ,
        source_scope=Scope.PUBLIC,
    )

    chunk = RetrievedChunk(
        text="Contenido recuperado.",
        metadata=metadata,
        score=0.87,
    )

    assert chunk.text == "Contenido recuperado."
    assert chunk.metadata.doc_id == "doc-1"
    assert chunk.score == 0.87


# ---------------------------------------------------------------------------
# RetrievalResult
# ---------------------------------------------------------------------------


def test_retrieval_result_defaults():
    result = RetrievalResult()

    assert result.chunks == []
    assert result.fiscal_year_used is None
    assert result.year_requested is None
    assert result.year_available is True
    assert result.best_score is None


def test_retrieval_result_preserves_chunks_and_year_information():
    metadata = ChunkMetadata(
        doc_id="doc-1",
        doc_type=DocType.LAW,
        source_scope=Scope.PUBLIC,
    )

    chunk = RetrievedChunk(
        text="Texto legal.",
        metadata=metadata,
        score=0.91,
    )

    result = RetrievalResult(
        chunks=[chunk],
        fiscal_year_used=2025,
        year_requested=2025,
        year_available=True,
        best_score=0.91,
    )

    assert result.chunks == [chunk]
    assert result.fiscal_year_used == 2025
    assert result.year_requested == 2025
    assert result.year_available is True
    assert result.best_score == 0.91


def test_retrieval_result_can_represent_unavailable_year():
    result = RetrievalResult(
        fiscal_year_used=None,
        year_requested=2024,
        year_available=False,
    )

    assert result.chunks == []
    assert result.fiscal_year_used is None
    assert result.year_requested == 2024
    assert result.year_available is False


# ---------------------------------------------------------------------------
# Source
# ---------------------------------------------------------------------------


def test_source_serializes_enum_as_value():
    source = Source(
        doc_id="doc-1",
        section_label="IVA",
        page=10,
        fiscal_year=2026,
        source_url="https://example.com",
        snippet="Texto relevante.",
        source_scope=Scope.PUBLIC,
    )

    assert source.source_scope == Scope.PUBLIC.value
    assert source.page == 10
    assert source.page_end == 0


def test_source_preserves_page_end():
    source = Source(
        doc_id="doc-1",
        section_label="IVA",
        page=10,
        page_end=12,
        fiscal_year=2026,
        source_url="https://example.com",
        snippet="Texto relevante.",
        source_scope=Scope.PUBLIC,
    )

    assert source.page == 10
    assert source.page_end == 12


# ---------------------------------------------------------------------------
# RagAnswer
# ---------------------------------------------------------------------------


def test_rag_answer_defaults_to_answered():
    answer = RagAnswer(answer="Respuesta.")

    assert answer.answer == "Respuesta."
    assert answer.sources == []
    assert answer.status == AnswerStatus.ANSWERED.value
    assert answer.fiscal_year_used is None


def test_rag_answer_preserves_status_and_sources():
    source = Source(
        doc_id="doc-1",
        section_label="IRPF",
        page=5,
        fiscal_year=2025,
        source_url="https://example.com",
        snippet="Fragmento relevante.",
        source_scope=Scope.PUBLIC,
    )

    answer = RagAnswer(
        answer="Respuesta basada en la fuente.",
        sources=[source],
        status=AnswerStatus.ANSWERED,
        fiscal_year_used=2025,
    )

    assert answer.answer == "Respuesta basada en la fuente."
    assert answer.sources == [source]
    assert answer.status == AnswerStatus.ANSWERED.value
    assert answer.fiscal_year_used == 2025


def test_rag_answer_supports_no_context_status():
    answer = RagAnswer(
        answer="No tengo contexto suficiente.",
        status=AnswerStatus.NO_CONTEXT,
    )

    assert answer.status == AnswerStatus.NO_CONTEXT.value
    assert answer.sources == []


# ---------------------------------------------------------------------------
# IngestReport
# ---------------------------------------------------------------------------


def test_ingest_report_defaults():
    report = IngestReport(
        doc_id="doc-1",
        chunks_indexed=10,
        pages=5,
    )

    assert report.doc_id == "doc-1"
    assert report.chunks_indexed == 10
    assert report.pages == 5
    assert report.redactions == 0
    assert report.warnings == []


def test_ingest_report_preserves_redactions_and_warnings():
    report = IngestReport(
        doc_id="doc-1",
        chunks_indexed=20,
        pages=8,
        redactions=3,
        warnings=["PII detected", "Missing source URL"],
    )

    assert report.redactions == 3
    assert report.warnings == [
        "PII detected",
        "Missing source URL",
    ]


# ---------------------------------------------------------------------------
# AskRequest
# ---------------------------------------------------------------------------


def test_ask_request_requires_question():
    with pytest.raises(ValidationError):
        AskRequest()


def test_ask_request_defaults_optional_fields():
    request = AskRequest(question="¿Qué es el IVA?")

    assert request.question == "¿Qué es el IVA?"
    assert request.session_id is None
    assert request.fiscal_year is None


def test_ask_request_preserves_session_and_fiscal_year():
    request = AskRequest(
        question="¿Qué IVA corresponde?",
        session_id="session-123",
        fiscal_year=2025,
    )

    assert request.question == "¿Qué IVA corresponde?"
    assert request.session_id == "session-123"
    assert request.fiscal_year == 2025
