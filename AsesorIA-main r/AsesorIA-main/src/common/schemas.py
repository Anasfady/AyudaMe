"""Shared data contracts between the four workstreams.
"""
from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class DocType(str, Enum):
    OFFICIAL_GUIDE = "official_guide"
    FAQ = "faq"
    LAW = "law"
    USER_UPLOAD = "user_upload"


class Scope(str, Enum):
    PUBLIC = "public"
    PRIVATE = "private"


class Tax(str, Enum):
    IRPF = "IRPF"
    IVA = "IVA"
    RETA = "RETA"
    GENERAL = "GENERAL"


class AnswerStatus(str, Enum):
    ANSWERED = "answered"
    NO_CONTEXT = "no_context"
    OUT_OF_SCOPE = "out_of_scope"
    YEAR_UNAVAILABLE = "year_unavailable"
    ERROR = "error"


class ChunkMetadata(BaseModel):
    """Metadata stored next to every chunk in the vector store."""

    model_config = ConfigDict(use_enum_values=True)

    doc_id: str
    tax: Tax = Tax.GENERAL
    doc_type: DocType
    # 0 means "not applicable / unknown" (typical for private uploads).
    fiscal_year: int = 0
    valid_from: str = ""
    valid_to: str = ""
    section_label: str = ""
    section_path: str = ""
    page: int = 0
    page_end: int = 0
    source_url: str = ""
    retrieved_at: str = ""
    source_scope: Scope
    session_id: str | None = None
    chunk_index: int = 0

    def to_store_dict(self) -> dict:
        """Chroma rejects None values, so drop them before indexing."""
        return {k: v for k, v in self.model_dump().items() if v is not None}


class RetrievedChunk(BaseModel):
    text: str
    metadata: ChunkMetadata
    score: float


class RetrievalResult(BaseModel):
    """What the retriever hands to the generation layer.

    It is richer than a plain list so the service can tell apart
    "no relevant chunks" from "the requested fiscal year is not indexed".
    """

    chunks: list[RetrievedChunk] = Field(default_factory=list)
    fiscal_year_used: int | None = None
    year_requested: int | None = None
    year_available: bool = True
    best_score: float | None = None


class Source(BaseModel):
    doc_id: str
    section_label: str
    page: int
    page_end: int = 0
    fiscal_year: int
    source_url: str
    snippet: str
    source_scope: Scope

    model_config = ConfigDict(use_enum_values=True)


class RagAnswer(BaseModel):
    answer: str
    sources: list[Source] = Field(default_factory=list)
    status: AnswerStatus = AnswerStatus.ANSWERED
    fiscal_year_used: int | None = None

    model_config = ConfigDict(use_enum_values=True)


class IngestReport(BaseModel):
    doc_id: str
    chunks_indexed: int
    pages: int
    redactions: int = 0
    warnings: list[str] = Field(default_factory=list)


class AskRequest(BaseModel):
    question: str
    session_id: str | None = None
    fiscal_year: int | None = None  # None = automatic
