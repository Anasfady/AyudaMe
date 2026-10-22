"""Text cleaning."""
from __future__ import annotations

import re
from collections import Counter

from src.ingestion.loaders import LoadedPage

# AEAT manuals prepend a rotating "dd/mm/yyyy - " revision date to the same
# repeated header/footer line (observed directly in the real Manual práctico
# de Renta PDFs), so an exact string match misses it. Strip that prefix before
# comparing lines for repetition.
_LEADING_DATE_RE = re.compile(r"^\d{1,2}/\d{1,2}/\d{2,4}\s*-\s*")

# BOE consolidated-legislation PDFs repeat a "Página N" footer on every page
# with a different N (observed on the real Orden PJC/178/2025 PDF), so an exact
# match never fires, each page's footer is technically a unique string. Only
# normalize lines that are this specific marker (whole line, case-insensitive);
# collapsing digits anywhere in any line is deliberately avoided; a first
# attempt at that also matched genuine content that merely differs by a number
# (e.g. two paragraphs that happen to both end in "el artículo 18" vs "19"),
# which would wrongly delete real, differing content instead of a repeated one.
_PAGE_MARKER_RE = re.compile(r"^p[aá]gina\s+\d+$", re.IGNORECASE)


def clean_text(text: str) -> str:
    """Fix hyphenated line breaks, collapse whitespace, keep paragraph breaks."""
    text = re.sub(r"(\w)-\n(\w)", r"\1\2", text)           # de-hyphenate
    text = re.sub(r"[ \t]+", " ", text)                    # collapse spaces
    text = re.sub(r"\n{3,}", "\n\n", text)                 # cap blank lines
    return text.strip()


def _normalize_for_dedup(line: str) -> str:
    """Normalize a line so header/footer variants still compare as equal:
    strip a leading rotating date, then collapse a whole-line "Página N" marker
    to a fixed placeholder (never touches digits inside other content)."""
    line = _LEADING_DATE_RE.sub("", line)
    if _PAGE_MARKER_RE.match(line):
        return "\0PAGE_MARKER\0"
    return line


def remove_repeated_lines(pages: list[LoadedPage], min_ratio: float = 0.5) -> list[LoadedPage]:
    """Remove lines (headers/footers) repeated on at least `min_ratio` of the pages.

    Compares lines after normalization (see _normalize_for_dedup), since both
    AEAT manuals (rotating date prefix) and BOE consolidated texts (per-page
    "Página N" footer) reuse the same header/footer text with a small varying
    part. An exact match would miss both and leave that noise in every chunk.

    The "Página N" normalization only matches a line that IS that marker in
    full, not digits appearing anywhere in a longer line, so it can't
    mistakenly conflate two different body lines that happen to both contain
    a number (see the comment above _PAGE_MARKER_RE for a concrete case this
    was written to avoid).
    """
    if len(pages) < 3:
        return pages
    counter: Counter[str] = Counter()
    for page in pages:
        seen_normalized = {_normalize_for_dedup(ln.strip()) for ln in page.text.splitlines() if ln.strip()}
        counter.update(seen_normalized)
    threshold = max(2, int(len(pages) * min_ratio))
    repeated_normalized = {line for line, count in counter.items() if count >= threshold}
    return [
        LoadedPage(
            text="\n".join(
                ln for ln in page.text.splitlines()
                if _normalize_for_dedup(ln.strip()) not in repeated_normalized
            ),
            page=page.page,
        )
        for page in pages
    ]
