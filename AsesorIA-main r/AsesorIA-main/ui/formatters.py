"""Presentation: turns contract data and UI states into Markdown text.

Pure, testable functions with no Chainlit or backend dependency.
The visible interface copy lives here so it can be reviewed and tested.
"""

from __future__ import annotations

from typing import Iterable, Optional, Sequence

try:
    from .contracts import RAGResponse, Source
except ImportError:
    from contracts import RAGResponse, Source

# --------------------------------------------------------------------------- #
# Individual source
# --------------------------------------------------------------------------- #


def format_source_header(source: Source, index: Optional[int] = None) -> str:
    """Source header: number, document and only the metadata that exists.

    Missing page/section/score are simply omitted (never padded with
    placeholder text); the label alone is valid when nothing else exists.
    """
    document = source.document or "Documento desconocido"
    label = f"**{index}. {document}**" if index is not None else f"**{document}**"

    parts: list[str] = []
    if source.page is not None:
        parts.append(f"pág. {source.page}")

    if source.section:
        parts.append(source.section)

    if source.score is not None:
        score = f"{source.score:.2f}".replace(".", ",")
        parts.append(f"relevancia {score}")

    if not parts:
        return label
    return f"{label} · " + " · ".join(parts)


def format_source_quote(source: Source) -> str:
    """Retrieved snippet rendered as a quote; placeholder when empty."""
    content = (source.content or "").strip()
    if not content:
        content = "(fragmento no disponible)"
    return f'> "{content}"'


def format_source(source: Source, index: Optional[int] = None) -> str:
    """Full source: header + quote."""
    return f"{format_source_header(source, index)}\n{format_source_quote(source)}"


def format_metadata(source: Source) -> str:
    """Compact provenance line (for headers or short messages)."""
    parts: list[str] = []
    if source.document:
        parts.append(source.document)
    if source.page is not None:
        parts.append(f"pág. {source.page}")
    if source.section:
        parts.append(source.section)
    return " · ".join(parts) if parts else "Origen desconocido"


def format_sources(sources: Iterable[Source]) -> str:
    """Numbered list of sources, without title."""
    src_list = list(sources)
    if not src_list:
        return ""
    return "\n\n".join(
        format_source(src, index=i + 1) for i, src in enumerate(src_list)
    )


def format_sources_block(sources: Sequence[Source]) -> str:
    """Full traceability block (title + sources).

    Returns an empty string when there are no sources: the UI hides the block.
    """
    src_list = list(sources)
    if not src_list:
        return ""
    n = len(src_list)
    title = f"**📄 Fuentes utilizadas · {n}**"
    return f"{title}\n\n{format_sources(src_list)}"


# --------------------------------------------------------------------------- #
# Answer
# --------------------------------------------------------------------------- #


def format_answer(response: RAGResponse) -> str:
    """Answer text (sources go in their own block)."""
    text = (response.answer or "").strip()
    if response.latency_ms is not None:
        text += f"\n\n---\n⏱️ *Latencia: {response.latency_ms:.0f} ms*"
    return text


def format_answer_block(response: RAGResponse) -> str:
    """Answer + sources block in a single message."""
    parts = [format_answer(response)]
    block = format_sources_block(response.sources)
    if block:
        parts.append(f"\n---\n\n{block}")
    return "\n".join(parts)


# --------------------------------------------------------------------------- #
# UI states
# --------------------------------------------------------------------------- #


def format_welcome(is_mock: bool = False) -> str:
    """Welcome message: identity, upload action, compact steps and grounding limit."""
    lines = [
        "**Asesor Fiscal IA**",
        "👉 Pulsa **Cargar documentación** (o usa el 📎 del editor) para empezar.",
        "",
        "**Cómo funciona**",
        "1️⃣ **Carga** · 2️⃣ **Pregunta** · 3️⃣ **Revisa las fuentes**",
        "",
        "> ⓘ Las respuestas se basan exclusivamente en la documentación disponible.",
    ]
    if is_mock:
        lines += [
            "",
            "🧠 *Modo demostración: las respuestas son simuladas.*",
        ]
    return "\n".join(lines)


def format_no_answer(response: RAGResponse) -> str:
    """'Not enough information' state (not a technical error)."""
    lines = [
        "**ℹ️ No he encontrado información suficiente**",
        "",
        "No hay en la documentación cargada una base suficiente para responder "
        "con seguridad a esta pregunta, así que prefiero no improvisar.",
    ]
    if response.no_answer_reason:
        lines += ["", f"*Motivo: {response.no_answer_reason}.*"]
    lines += [
        "",
        "*Puedes cargar documentación relevante o reformular la pregunta.*",
    ]
    return "\n".join(lines)


def format_error(kind: str = "unknown") -> str:
    """Technical error state, with no internal details.

    kind: "connection" (engine unavailable) | "backend" | "unknown".
    """
    if kind == "connection":
        return (
            "**⚠️ No he podido conectar con el motor de consulta**\n\n"
            "El servicio de búsqueda no está disponible ahora mismo. "
            "Inténtalo de nuevo en unos segundos."
        )
    return (
        "**⚠️ Se ha producido un error técnico**\n\n"
        "No he podido completar tu consulta. Inténtalo de nuevo en unos "
        "segundos; si persiste, avisa al equipo del proyecto."
    )


def format_file_error(filename: str, reason: str) -> str:
    """Upload error for a specific file (type, size, empty or unreadable)."""
    reasons = {
        "type": f"No puedo aceptar «{filename}». Usa archivos PDF, TXT o Markdown.",
        "size": f"«{filename}» supera el tamaño máximo permitido (50 MB).",
        "empty": f"«{filename}» está vacío y no se puede consultar.",
        "read": f"No se ha podido leer «{filename}». Vuelve a subirlo.",
    }
    detail = reasons.get(reason, reasons["read"])
    return f"**⚠️ Problema con la carga**\n\n{detail}"


def format_documents_state(names: Sequence[str]) -> str:
    """Visible state of the documentation loaded in the session."""
    unique = list(dict.fromkeys(names))
    n = len(unique)
    noun = "documento" if n == 1 else "documentos"
    title = f"**📚 Documentación disponible · {n} {noun}**"
    if not unique:
        return f"{title}\n\n_(sin archivos)_"
    listing = "\n".join(f"✓ {name}" for name in unique)
    return f"{title}\n\n{listing}"


def format_no_documents() -> str:
    """'No documentation loaded' state (not an error)."""
    return (
        "**📚 Todavía no hay documentación cargada**\n\n"
        "Carga tu documentación para empezar: la responderé solo con ella.\n\n"
        "Admite PDF, TXT y Markdown — usa el botón *Cargar documentación* "
        "o el 📎 del editor."
    )


def format_empty_question() -> str:
    """Friendly reminder when a message is sent without a question."""
    return (
        "Escribe una pregunta para poder ayudarte. "
        "Por ejemplo: *¿Qué gastos son deducibles de un autónomo?*"
    )


def format_clarify(has_docs: bool = False, in_conversation: bool = False) -> str:
    """Orientation state for clearly vague openers (never sent to the RAG).

    Context-aware: mentions the loaded documentation when there is one,
    invites to load it when there is none, and nudges the chat when the
    conversation already started. The suggestion buttons (rendered by the
    caller as real actions) are orientation only — they never claim the
    documentation contains that information.
    """
    headline = "**Claro. Puedo ayudarte a consultar la documentación disponible.**"
    if has_docs:
        context = "Tienes documentación cargada."
    else:
        context = "Carga tu documentación para empezar: admite PDF, TXT y Markdown."
    if in_conversation:
        context += " Sigue preguntando por lo que te interese."
    return f"{headline}\n\n**¿Qué te interesa?**\n\n{context}"


def format_question_too_long(limit: int) -> str:
    """Warning for an excessively long question."""
    return (
        f"Tu pregunta es demasiado larga (máximo {limit} caracteres). "
        "Divídela en consultas más concretas para obtener una respuesta más precisa."
    )


# --------------------------------------------------------------------------- #
# Errors (compatibility)
# --------------------------------------------------------------------------- #


def format_error_message(exc: BaseException, kind: str = "unknown") -> str:
    """Friendly error message derived from an exception (never exposes details)."""
    if isinstance(exc, (ConnectionError, TimeoutError)):
        return format_error("connection")
    return format_error(kind)
