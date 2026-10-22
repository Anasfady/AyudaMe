"""Lightweight conversational UX guidance — no model, no classifier.

A purely lexical rule routes obviously vague or purely conversational
messages («hola», «ayuda», «me puedes guiar?», «qué me puedes decir?»,
«algo más?», «no sé qué preguntar»…) to a friendly orientation state with
real suggestion actions instead of the RAG backend, which would otherwise
answer them with the same generic reply.

The rule is intentionally simple, transparent and maintainable:

    the WHOLE message, normalized (lowercase, no accents, no punctuation,
    collapsed whitespace), must equal one of AMBIGUOUS_PHRASES.

Consequences by design:

* «hola», «¡ayuda!», «ME PUEDES GUIAR?», «¿qué puedo preguntar?» → guided;
* «Explícame el IVA» → NOT ambiguous (broad but legitimate → RAG);
* «¿Qué me puedes decir sobre las retenciones?» → NOT ambiguous (RAG);
* «IRPF», «¿cuándo se presenta el 303?» → NOT ambiguous (RAG).

Nothing here talks to the backend: `app.py` keeps the architecture
app.py → rag_adapter.py → RAG.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Tuple

# (visible label, example question) — orientation, not a corpus promise:
# they only show where to go next, never claim the documentation contains
# that information.
GUIDANCE_SUGGESTIONS: Tuple[Tuple[str, str], ...] = (
    ("Alta de autónomo", "¿Cómo me doy de alta como autónomo?"),
    ("IVA", "¿Qué es el IVA soportado y cómo se deduce?"),
    ("IRPF", "¿Qué gastos son deducibles en el IRPF de un autónomo?"),
    ("Gastos deducibles", "¿Qué gastos puedo deducir como autónomo?"),
    ("Obligaciones fiscales", "¿Qué obligaciones fiscales tengo como autónomo?"),
)

# How many suggestions remain once the conversation has already started
# (the chat itself takes priority over orientation buttons).
GUIDANCE_SUGGESTIONS_WHILE_CHAT = 2

_AMBIGUOUS_PHRASES = frozenset(
    {
        # greetings
        "hola",
        "holas",
        "buenas",
        "buenos dias",
        "buenas tardes",
        "buenas noches",
        "que tal",
        "hey",
        "adios",
        "gracias",
        # requests for help / meta questions
        "ayuda",
        "ayudame",
        "help",
        "que puedo preguntar",
        "que preguntas puedo hacer",
        "que me puedes preguntar",
        "que me puedes decir",
        "que me puede decir",
        "me puedes guiar",
        "puedes guiarme",
        "guiame",
        "no se que preguntar",
        "no se que decir",
        "no se que hacer",
        "algo mas",
        "hay algo mas",
        "que mas",
        "ejemplos",
        "ejemplo",
        "sugerencias",
        "sugerencia",
        "que sabes",
        "que haces",
        "informacion",
        "informacion general",
        # vague intent / empty thinking
        "no se",
        "nose",
        "explicame",
        "explica",
        "explicamelo",
    }
)

_PUNCT_RE = re.compile(r"[¿?¡!.,;:…]+")
_SPACE_RE = re.compile(r"\s+")


def normalize_query(text: str) -> str:
    """Lowercase, drop accents and punctuation, collapse whitespace."""
    lowered = unicodedata.normalize("NFD", (text or "").lower())
    without_marks = "".join(ch for ch in lowered if not unicodedata.combining(ch))
    without_punct = _PUNCT_RE.sub(" ", without_marks)
    return _SPACE_RE.sub(" ", without_punct).strip()


def is_ambiguous(question: str) -> bool:
    """True only for exact-match vague openers (see module docstring).

    Empty/blank input is NOT ambiguous: the caller handles it with the
    dedicated «empty question» state before consulting this rule.
    """
    normalized = normalize_query(question)
    if not normalized:
        return False
    return normalized in _AMBIGUOUS_PHRASES
