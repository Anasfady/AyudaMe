"""Tokenizer y formato compartidos por chunking y la futura indexación.

No carga pesos del modelo, no calcula embeddings y nunca trunca el texto.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


class Tokenizer(Protocol):
    model_max_length: int

    def encode(self, text: str, *, add_special_tokens: bool,
               truncation: bool) -> list[int]: ...


@dataclass(frozen=True)
class Tokenization:
    tokenizer: Tokenizer
    max_input_tokens: int
    passage_prefix: str = ""

    def __post_init__(self):
        if type(self.max_input_tokens) is not int or self.max_input_tokens <= 0:
            raise ValueError("max_input_tokens debe ser un entero positivo")
        known_limit = getattr(self.tokenizer, "model_max_length", None)
        if isinstance(known_limit, int) and known_limit < 1_000_000:
            if self.max_input_tokens > known_limit:
                raise ValueError("El límite configurado supera el del tokenizer")

    def count(self, text: str, *, special_tokens: bool = True) -> int:
        return len(self.tokenizer.encode(
            text, add_special_tokens=special_tokens, truncation=False,
        ))

    def prepare(self, text: str, label: str = "", path: str = "") -> str:
        # El contexto se añade una sola vez aquí. El futuro embedder debe usar
        # este mismo resultado, sin volver a añadir el prefijo o el título.
        context = list(dict.fromkeys(value.strip() for value in (path, label)
                                    if value.strip()))
        body = "\n".join(context) + "\n\n" + text if context else text
        return self.passage_prefix + body


def load_tokenization(settings=None) -> Tokenization:
    """Carga solo el tokenizer asociado a Settings.embedding_model.

    La carga se hace explícitamente fuera del algoritmo de chunking.
    Para otro modelo, revisar también prefijo y límite en Settings.
    """
    from transformers import AutoTokenizer
    from src.common.settings import get_settings

    settings = settings or get_settings()
    tokenizer = AutoTokenizer.from_pretrained(settings.embedding_model)
    limit = settings.embedding_max_tokens
    if limit is None:
        limit = tokenizer.model_max_length
        # Hugging Face usa un número enorme cuando desconoce el límite.
        if not isinstance(limit, int) or limit >= 1_000_000:
            raise ValueError("Configura embedding_max_tokens para este modelo")
    return Tokenization(tokenizer, limit, settings.embedding_passage_prefix)
