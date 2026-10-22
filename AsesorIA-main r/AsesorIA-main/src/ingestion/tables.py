"""Table extraction.

Tables extract badly with plain text loaders, so they are handled separately and
converted to Markdown-like text before chunking.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pdfplumber


@dataclass
class ExtractedTable:
    page: int
    markdown: str


def _clean_cell(value: str | None) -> str:
    """A None cell means "not part of this table" and stays empty; a real
    string may contain embedded newlines from a wrapped header (observed on
    the real Orden PJC/178/2025 tables, e.g. "Base mínima\\n–\\nEuros/mes")."""
    if value is None:
        return ""
    return " ".join(value.split())


def _forward_fill(rows: list[list[str | None]]) -> list[list[str]]:
    """pdfplumber emits None for a cell covered by a vertical span (e.g. the
    "Tabla reducida" / "Tabla general" label column, which only carries a
    value on the first of several rows it visually spans). Carry the last
    seen value down each column so every row is self-contained once it
    becomes a standalone Markdown row — a plain None-to-"" conversion would
    silently drop which section a tramo row belongs to.

    Known limitation (observed on the real Orden PJC/178/2025 table): the
    very first row of a spanned section sometimes comes through as "" rather
    than None, so that one row's label stays blank instead of inheriting the
    section name. Forward-filling "" as well would fix it here but risks
    papering over a genuinely blank cell in some other table; left as a
    cosmetic gap rather than guessing.
    """
    if not rows:
        return []
    num_cols = max(len(r) for r in rows)
    last_seen: list[str] = [""] * num_cols
    filled: list[list[str]] = []
    for row in rows:
        padded = list(row) + [None] * (num_cols - len(row))
        result = []
        for col, cell in enumerate(padded):
            if cell is None:
                result.append(last_seen[col])
            else:
                cleaned = _clean_cell(cell)
                result.append(cleaned)
                last_seen[col] = cleaned
        filled.append(result)
    return filled


def _table_to_markdown(rows: list[list[str | None]]) -> str:
    """Render a pdfplumber table as a Markdown table.

    Heuristic: the first row is treated as the header. This holds for every
    table observed in the RETA corpus (RDL 13/2022, Orden PJC/178/2025) but
    would be wrong for a table with no header row — if a future document
    needs that, this function will need a per-call flag rather than guessing.
    """
    filled = _forward_fill(rows)
    if not filled:
        return ""
    header, *body = filled
    lines = [
        "| " + " | ".join(header) + " |",
        "| " + " | ".join("---" for _ in header) + " |",
    ]
    lines.extend("| " + " | ".join(row) + " |" for row in body)
    return "\n".join(lines)


def extract_tables(path: Path) -> list[ExtractedTable]:
    """Extract every table from a PDF, one ExtractedTable per detected table.

    Tables with fewer than 2 rows (header only, or a stray one-cell match) are
    skipped as noise rather than emitted as a degenerate "table".
    """
    results: list[ExtractedTable] = []
    with pdfplumber.open(str(path)) as pdf:
        for page in pdf.pages:
            for raw_table in page.extract_tables():
                if len(raw_table) < 2:
                    continue
                markdown = _table_to_markdown(raw_table)
                if markdown:
                    results.append(ExtractedTable(page=page.page_number, markdown=markdown))
    return results
