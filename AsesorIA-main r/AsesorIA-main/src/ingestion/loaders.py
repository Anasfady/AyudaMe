"""Document loaders (PDF, TXT, Markdown)."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from pypdf import PdfReader

from src.common.errors import UnreadableDocumentError, UnsupportedFileTypeError


SUPPORTED_SUFFIXES = {".pdf", ".txt", ".md"}


@dataclass
class LoadedPage:
    text: str
    page: int  # 1-based


def load_document(path: Path) -> list[LoadedPage]:
    """Load a document and return one LoadedPage per PDF page (or a single page)."""
    suffix = path.suffix.lower()
    if suffix not in SUPPORTED_SUFFIXES:
        raise UnsupportedFileTypeError(f"Unsupported file type: {suffix}")
    if suffix == ".pdf":
        return _load_pdf(path)
    return [LoadedPage(text=path.read_text(encoding="utf-8", errors="ignore"), page=1)]


def _load_pdf(path: Path) -> list[LoadedPage]:
    reader = PdfReader(str(path))
    pages = [
        LoadedPage(text=(page.extract_text() or ""), page=index + 1)
        for index, page in enumerate(reader.pages)
    ]
    if not any(p.text.strip() for p in pages):
        # TODO: optional OCR fallback.
        raise UnreadableDocumentError(f"No extractable text in {path.name}")
    return pages
