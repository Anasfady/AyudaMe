"""Contracts between frontend and backend RAG.

Defines the canonical data structures that the backend must return.
The adapter in rag_adapter.py normalizes whatever the backend produces
into these types so that app.py never touches raw backend objects.

Normalization is deliberately tolerant: missing, ``None``, wrongly typed or
object-shaped optional metadata must NEVER raise.  The UI degrades
gracefully (missing page/section simply omitted from the header, score
omitted) instead of breaking.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Optional

# Keys consulted (in order) when the canonical field is missing.  They cover
# both the documented contract and common shapes produced by RAG backends
# (LangChain-style documents use ``source``/``page_content``/``page``).
_DOCUMENT_KEYS = (
    "document", "source", "filename", "file", "doc", "path", "source_url", "doc_id"
)
_CONTENT_KEYS = ("content", "text", "page_content", "chunk", "fragment")
# "section_label"/"section_path": the real retrieval metadata (PRs #25-#28)
# never uses a plain ``section`` key; the canonical one is preferred first.
_SECTION_KEYS = ("section", "section_label", "section_path", "heading")
_PAGE_KEYS = ("page", "page_number", "pág", "pagina")
_SCORE_KEYS = ("score", "relevance", "relevance_score", "similarity")

_TRUE_STRINGS = {"true", "1", "yes", "y", "si", "sí"}
_FALSE_STRINGS = {"false", "0", "no", "n", ""}


def _basename(value: str) -> str:
    """Keep only the file name of a path (either separator)."""
    return re.split(r"[\\/]", value.strip())[-1].strip() or value.strip()


def _as_text(value: Any) -> Optional[str]:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _as_optional_int(value: Any) -> Optional[int]:
    if value is None or isinstance(value, bool):
        return None
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


def _as_optional_float(value: Any) -> Optional[float]:
    if value is None or isinstance(value, bool):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _as_optional_dict(value: Any) -> Optional[dict]:
    return value if isinstance(value, dict) else None


def _as_bool(value: Any, default: bool) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in _TRUE_STRINGS:
            return True
        if normalized in _FALSE_STRINGS:
            return False
    return default


def _pick(mapping: Any, keys: tuple, cast) -> Any:
    """First usable value for ``keys`` in ``mapping`` (a dict), casted."""
    if not isinstance(mapping, dict):
        return None
    for key in keys:
        if key in mapping:
            value = cast(mapping.get(key))
            if value is not None:
                return value
    return None


@dataclass
class Source:
    """A single retrieved source chunk.

    All fields are optional except ``document`` and ``content`` which the
    backend should always provide.  The frontend gracefully degrades when
    any of the optional fields is ``None``.
    """

    document: str
    content: str
    page: Optional[int] = None
    section: Optional[str] = None
    score: Optional[float] = None
    metadata: Optional[dict] = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Source":
        """Build a Source from a plain dict, tolerating missing keys.

        Values may also live inside ``metadata`` (common in chunk objects);
        the top-level field always wins.  Unusable values become ``None``
        instead of raising.
        """
        metadata = _as_optional_dict(data.get("metadata"))

        document = _as_text(data.get("document")) or _pick(
            metadata, _DOCUMENT_KEYS, _as_text
        )
        content = _as_text(data.get("content")) or _pick(
            metadata, _CONTENT_KEYS, _as_text
        )
        page = _as_optional_int(data.get("page"))
        if page is None:
            page = _as_optional_int(_pick(metadata, _PAGE_KEYS, _as_optional_int))
        section = _as_text(data.get("section")) or _pick(
            metadata, _SECTION_KEYS, _as_text
        )
        score = _as_optional_float(data.get("score"))
        if score is None:
            score = _as_optional_float(_pick(metadata, _SCORE_KEYS, _as_optional_float))

        return cls(
            document=_basename(document) if document else "unknown",
            content=content or "",
            page=page,
            section=section,
            score=score,
            metadata=metadata,
        )

    @classmethod
    def from_any(cls, obj: Any) -> "Source":
        """Build a Source from any object: dict, Source, document-like object
        (attributes such as ``page_content``/``metadata``) or plain text."""
        if isinstance(obj, Source):
            return obj
        if isinstance(obj, dict):
            return cls.from_dict(obj)
        if (
            hasattr(obj, "page_content")
            or hasattr(obj, "metadata")
            or hasattr(obj, "content")
            or hasattr(obj, "text")
        ):
            # Duck-typed document objects (LangChain-style, no import needed).
            metadata = getattr(obj, "metadata", None)
            payload: dict[str, Any] = {
                "document": getattr(obj, "source", None)
                or getattr(obj, "document", None)
                or getattr(obj, "filename", None),
                "content": getattr(obj, "page_content", None)
                or getattr(obj, "content", None)
                or getattr(obj, "text", None),
                "page": getattr(obj, "page", None),
                "section": getattr(obj, "section", None),
                "score": getattr(obj, "score", None),
                "metadata": metadata if isinstance(metadata, dict) else None,
            }
            return cls.from_dict(payload)
        # Fallback: treat as a plain string chunk with unknown provenance.
        return cls(document="unknown", content=str(obj))


@dataclass
class RAGResponse:
    """Canonical response returned by the RAG adapter.

    The frontend consumes only this structure.  The adapter is responsible
    for translating whatever the real backend returns into this shape.
    """

    answer: str
    sources: list[Source] = field(default_factory=list)
    grounded: bool = True
    no_answer_reason: Optional[str] = None
    latency_ms: Optional[float] = None
    # Optional structured breakdown for a chart widget (demo/mock or any
    # backend that can provide it): {"title", "labels": [...], "values": [...],
    # "y_label"}.  Purely optional — the UI renders a cl.Plotly element when
    # present and simply skips it when missing, so real backends are
    # unaffected.
    chart: Optional[dict] = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "RAGResponse":
        """Build a RAGResponse from a plain dict, normalizing sources.

        ``sources`` accepts a list, a tuple, a single source or ``None``.
        When absent, the real backend key ``source_documents``
        (``RAGPipeline.answer_query``) is used instead.
        ``grounded`` accepts booleans and common string encodings; when it
        is missing, a non-empty ``no_answer_reason`` implies ``False``.
        """
        raw_sources = data.get("sources")
        if raw_sources is None:
            # Real backend shape: RAGPipeline.answer_query() returns
            # {"answer", "source_documents"} — no "sources" key.
            raw_sources = data.get("source_documents")
        if raw_sources is None:
            source_list: list[Any] = []
        elif isinstance(raw_sources, (list, tuple, set)):
            source_list = list(raw_sources)
        else:
            source_list = [raw_sources]  # single dict/object/str

        reason = _as_text(data.get("no_answer_reason"))
        return cls(
            answer=_as_text(data.get("answer")) or "",
            sources=[Source.from_any(s) for s in source_list],
            grounded=_as_bool(data.get("grounded"), default=reason is None),
            no_answer_reason=reason,
            latency_ms=_as_optional_float(data.get("latency_ms")),
            chart=_as_optional_dict(data.get("chart")),
        )

    @classmethod
    def from_any(cls, obj: Any) -> "RAGResponse":
        """Build a RAGResponse from any object: dict, RAGResponse,
        response-like object (attributes) or str."""
        if isinstance(obj, RAGResponse):
            return obj
        if isinstance(obj, dict):
            return cls.from_dict(obj)
        if obj is None:
            # A backend returning nothing is treated as "no information",
            # never as the literal text "None".
            return cls(answer="", sources=[], grounded=False,
                       no_answer_reason="el motor no devolvió respuesta")
        if (
            hasattr(obj, "answer")
            or hasattr(obj, "sources")
            or hasattr(obj, "source_documents")
        ):
            payload = {
                "answer": getattr(obj, "answer", None) or getattr(obj, "text", None),
                "sources": getattr(obj, "sources", None)
                or getattr(obj, "source_documents", None),
                "grounded": getattr(obj, "grounded", None),
                "no_answer_reason": getattr(obj, "no_answer_reason", None)
                or getattr(obj, "reason", None),
                "latency_ms": getattr(obj, "latency_ms", None),
                "chart": getattr(obj, "chart", None),
            }
            return cls.from_dict(payload)
        # Fallback: plain text answer with no sources.
        return cls(answer=str(obj), sources=[], grounded=False)

    @property
    def has_answer(self) -> bool:
        """True when there is a non-empty answer."""
        return bool(self.answer and self.answer.strip())

    @property
    def has_sources(self) -> bool:
        """True when at least one source is available."""
        return len(self.sources) > 0
