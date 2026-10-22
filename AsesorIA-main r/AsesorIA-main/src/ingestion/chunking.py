"""Chunking por tokens con trazabilidad de caracteres y metadatos compartidos.

Entrada pública: chunk_document. No genera embeddings ni escribe en Chroma.
"""
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
import re
from typing import Sequence

from src.common.schemas import ChunkMetadata
from src.common.tokenization import Tokenization
from src.ingestion.loaders import LoadedPage


@dataclass(frozen=True)
class ChunkingConfig:
    # Presupuesto TOTAL: prefijo, contexto, contenido y tokens especiales.
    max_tokens: int
    overlap_tokens: int
    detect_markdown_headings: bool = False

    def __post_init__(self):
        if type(self.max_tokens) is not int or type(self.overlap_tokens) is not int:
            raise TypeError("Los tamaños en tokens deben ser enteros")
        if self.max_tokens <= 0 or not 0 <= self.overlap_tokens < self.max_tokens:
            raise ValueError("Se requiere 0 <= overlap_tokens < max_tokens")

    @classmethod
    def from_settings(cls, settings):
        if settings.chunk_size_tokens is None or settings.chunk_overlap_tokens is None:
            raise ValueError("Selecciona tamaño y overlap en tokens")
        return cls(settings.chunk_size_tokens, settings.chunk_overlap_tokens)


@dataclass(frozen=True)
class SectionSpan:
    """Sección fiable en el texto unido, con final excluido.

    Puede recibirse desde una capa previa. No se permite texto reescrito:
    start/end siempre se refieren al mismo texto que el mapa de páginas.
    """
    start: int
    end: int
    section_label: str = ""
    section_path: str = ""


@dataclass(frozen=True)
class Chunk:
    text: str
    embedding_text: str
    metadata: ChunkMetadata
    start: int
    end: int
    token_count: int
    overlap_tokens: int


def join_pages_with_spans(pages: Sequence[LoadedPage]):
    """Une páginas en orden; conserva números y offsets de caracteres."""
    parts, spans = [], []
    position = 0
    previous_page = 0
    for index, page in enumerate(pages):
        if not isinstance(page.text, str):
            raise TypeError("El texto de cada página debe ser una cadena")
        if type(page.page) is not int or page.page <= previous_page:
            raise ValueError("Las páginas deben ser positivas y estar en orden creciente")
        previous_page = page.page
        if index:
            parts.append("\n")
            position += 1
        start = position
        parts.append(page.text)
        position += len(page.text)
        spans.append({"page": page.page, "start": start, "end": position})
    return "".join(parts), spans


def get_page_range(start: int, end: int, spans: list[dict]) -> tuple[int, int]:
    """Obtiene páginas usando caracteres, independientemente del tokenizer."""
    if type(start) is not int or type(end) is not int:
        raise TypeError("start y end deben ser enteros")
    if start < 0 or end <= start:
        raise ValueError("El fragmento debe cumplir 0 <= start < end")
    if not spans or end > spans[-1]["end"]:
        raise ValueError("El fragmento está fuera del texto del mapa")
    pages = [s["page"] for s in spans if s["start"] < s["end"]
             and start < s["end"] and end > s["start"]]
    if not pages:
        raise ValueError("El fragmento no contiene texto de ninguna página")
    return pages[0], pages[-1]


def _markdown_sections(text: str) -> list[SectionSpan]:
    """Solo encabezados ATX explícitos; no infiere títulos visuales de PDF.

    Ignora encabezados dentro de bloques de código cercados. Conserva el
    texto de los encabezados en la fuente para mantener la trazabilidad.
    """
    headings, stack = [], []
    offset = 0
    fence_char, fence_length = "", 0
    for line in text.splitlines(keepends=True):
        fence = re.match(r"^ {0,3}(`{3,}|~{3,})(.*)$", line.rstrip("\r\n"))
        if fence:
            marker, rest = fence.groups()
            if not fence_char:
                fence_char, fence_length = marker[0], len(marker)
            elif marker[0] == fence_char and len(marker) >= fence_length and not rest.strip():
                fence_char = ""
        elif not fence_char:
            match = re.match(r"^ {0,3}(#{1,6})[ \t]+(.+?)\s*$", line)
            if match:
                level = len(match[1])
                label = re.sub(r"[ \t]+#+[ \t]*$", "", match[2]).strip()
                if label:
                    while stack and stack[-1][0] >= level:
                        stack.pop()
                    stack.append((level, label))
                    headings.append((offset, label, " > ".join(t for _, t in stack)))
        offset += len(line)
    return [SectionSpan(start, headings[i + 1][0] if i + 1 < len(headings) else len(text),
                        label, path)
            for i, (start, label, path) in enumerate(headings)]


def _complete_sections(text: str, sections: Sequence[SectionSpan],
                       metadata: ChunkMetadata) -> list[SectionSpan]:
    """Los huecos se conservan como texto sin una sección nueva inventada."""
    result, cursor = [], 0
    for section in sections:
        if (type(section.start) is not int or type(section.end) is not int
                or not cursor <= section.start < section.end <= len(text)):
            raise ValueError("Las secciones deben estar ordenadas, dentro del texto y sin solaparse")
        if cursor < section.start:
            result.append(SectionSpan(cursor, section.start,
                                      metadata.section_label, metadata.section_path))
        result.append(section)
        cursor = section.end
    if cursor < len(text):
        result.append(SectionSpan(cursor, len(text), metadata.section_label, metadata.section_path))
    return result


def _units(text: str, start: int, end: int, fits, separator_index=0):
    """División recursiva con offsets; cada decisión de tamaño usa tokens."""
    if fits(start, end):
        return [(start, end)]
    separators = ("\n\n", "\n", " ")
    if separator_index == len(separators):
        # Corte final por posiciones originales, nunca decode(tokens): así
        # no cambiamos acentos/espacios ni perdemos procedencia. El criterio
        # para aceptar cada mitad sigue siendo su conteo de tokens completo.
        if end - start <= 1:
            raise ValueError("El presupuesto no permite contexto y un carácter de contenido")
        middle = (start + end) // 2
        return (_units(text, start, middle, fits, separator_index)
                + _units(text, middle, end, fits, separator_index))
    separator = separators[separator_index]
    result, cursor = [], start
    while cursor < end:
        found = text.find(separator, cursor, end)
        boundary = end if found == -1 else found + len(separator)
        result.extend(_units(text, cursor, boundary, fits, separator_index + 1))
        cursor = boundary
    return result


def _section_chunks(text: str, section: SectionSpan, config: ChunkingConfig,
                    tokenization: Tokenization):
    if not text[section.start:section.end].strip():
        return []

    @lru_cache(maxsize=4096)
    def count(start, end):
        prepared = tokenization.prepare(text[start:end].strip(),
                                        section.section_label, section.section_path)
        return tokenization.count(prepared)

    def fits(start, end):
        return count(start, end) <= config.max_tokens

    if count(section.start, section.start) >= config.max_tokens:
        raise ValueError("El contexto consume el presupuesto: revisa título o max_tokens")

    units = _units(text, section.start, section.end, fits)
    chunks, current = [], []

    def save():
        start, end = current[0][0], current[-1][1]
        raw = text[start:end]
        start += len(raw) - len(raw.lstrip())
        end -= len(raw) - len(raw.rstrip())
        if start >= end:
            return
        prepared = tokenization.prepare(text[start:end], section.section_label, section.section_path)
        size = tokenization.count(prepared)
        if size > config.max_tokens:
            raise ValueError("El texto final supera el presupuesto de tokens")
        chunks.append((start, end, prepared, size))

    for unit in units:
        if current and not fits(current[0][0], unit[1]):
            save()
            while current:
                candidate_start = current[0][0]
                candidate = text[candidate_start:unit[1]]
                candidate_start += len(candidate) - len(candidate.lstrip())
                previous_end = chunks[-1][1] if chunks else section.start
                suffix = text[candidate_start:previous_end] if candidate_start < previous_end else ""
                overlap = tokenization.count(suffix, special_tokens=False)
                if (config.overlap_tokens > 0 and overlap <= config.overlap_tokens
                        and fits(current[0][0], unit[1])):
                    break
                current.pop(0)
        current.append(unit)
    if current:
        save()
    return chunks


def chunk_document(
    pages: Sequence[LoadedPage], metadata: ChunkMetadata, *,
    config: ChunkingConfig, tokenization: Tokenization,
    sections: Sequence[SectionSpan] | None = None,
) -> list[Chunk]:
    """Páginas + metadatos -> chunks medidos en tokens, sin embeddings.

    sections usa offsets del texto de join_pages_with_spans(pages). Recibe
    secciones fiables de otra capa o, opcionalmente, detecta títulos Markdown.
    No se deben limpiar/modificar textos después de calcular sus secciones.
    La numeración chunk_index comienza en cero y es global por documento.
    """
    if config.max_tokens > tokenization.max_input_tokens:
        raise ValueError("max_tokens supera el límite de entrada del modelo")
    if metadata.source_scope == "private" and not metadata.session_id:
        raise ValueError("Los documentos privados requieren session_id")
    text, page_spans = join_pages_with_spans(pages)
    if sections is not None and config.detect_markdown_headings:
        raise ValueError("Usa secciones explícitas o detección Markdown, no ambas")
    detected = (_markdown_sections(text) if config.detect_markdown_headings
                else sections if sections is not None else [])
    result = []
    for section in _complete_sections(text, detected, metadata):
        previous_end = section.start
        for start, end, prepared, count in _section_chunks(text, section, config, tokenization):
            page, page_end = get_page_range(start, end, page_spans)
            fields = metadata.model_dump()
            fields.update(page=page, page_end=page_end, section_label=section.section_label,
                          section_path=section.section_path, chunk_index=len(result))
            chunk_metadata = ChunkMetadata.model_validate(fields)
            overlap = tokenization.count(text[start:previous_end], special_tokens=False) if start < previous_end else 0
            # El recorte de espacios puede cambiar la tokenización del sufijo;
            # este valor registra el overlap REAL, no solo el configurado.
            result.append(Chunk(text[start:end], prepared, chunk_metadata,
                                start, end, count, overlap))
            previous_end = end
    return result
