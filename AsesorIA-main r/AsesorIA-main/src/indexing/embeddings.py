"""Embeddings de documentos preparados y consultas; sin almacenamiento ni retrieval."""
from __future__ import annotations

from functools import lru_cache
from typing import Sequence, TYPE_CHECKING

from src.common.settings import Settings, get_settings
from src.common.tokenization import Tokenization

if TYPE_CHECKING:
    from src.ingestion.chunking import Chunk


class EmbeddingService:
    """Reutiliza un modelo por instancia; model permite inyección en tests."""

    def __init__(self, settings: Settings | None = None, *, model=None,
                 batch_size: int = 32):
        if type(batch_size) is not int or batch_size <= 0:
            raise ValueError("batch_size debe ser un entero positivo")
        settings = settings or get_settings()
        if model is None:
            from sentence_transformers import SentenceTransformer
            model = SentenceTransformer(settings.embedding_model)
        self._model = model
        self.batch_size = batch_size
        # El límite efectivo incluye el del ejecutor, que puede ser menor
        # que el declarado por el tokenizer. Nunca dejamos que encode recorte.
        limit = model.max_seq_length
        if settings.embedding_max_tokens is not None:
            if settings.embedding_max_tokens <= 0:
                raise ValueError("embedding_max_tokens debe ser positivo")
            limit = min(limit, settings.embedding_max_tokens)
        self._tokenization = Tokenization(model.tokenizer, limit)

    @staticmethod
    def _validate_text(text: str, label: str) -> None:
        if not isinstance(text, str):
            raise TypeError(f"{label} debe ser una cadena")
        if not text.strip():
            raise ValueError(f"{label} no puede estar vacío")

    def _encode(self, texts: list[str]) -> list[list[float]]:
        for index, text in enumerate(texts):
            count = self._tokenization.count(text)
            if count > self._tokenization.max_input_tokens:
                raise ValueError(
                    f"Texto {index}: {count} tokens supera el límite "
                    f"{self._tokenization.max_input_tokens}; no se truncará"
                )
        vectors = self._model.encode(
            texts, batch_size=self.batch_size, normalize_embeddings=True,
            convert_to_numpy=True, show_progress_bar=False, prompt="",
        )
        # prompt vacío desactiva prefijos automáticos del modelo: los textos
        # ya están preparados. Listas simples mantienen independiente la API.
        return vectors.tolist()

    def embed_documents(self, embedding_texts: Sequence[str]) -> list[list[float]]:
        """Un vector por embedding_text, en el mismo orden, sin añadir prefijos."""
        if isinstance(embedding_texts, (str, bytes)):
            raise TypeError("embedding_texts debe ser una secuencia de textos")
        texts = list(embedding_texts)
        if not texts:
            raise ValueError("embedding_texts no puede estar vacío")
        for index, text in enumerate(texts):
            self._validate_text(text, f"embedding_texts[{index}]")
        return self._encode(texts)

    def embed_chunks(self, chunks: Sequence[Chunk]) -> list[list[float]]:
        """Adaptador: utiliza exclusivamente Chunk.embedding_text."""
        return self.embed_documents([chunk.embedding_text for chunk in chunks])

    def embed_query(self, query: str) -> list[float]:
        """Recibe una pregunta sin preparar y aplica la convención E5."""
        self._validate_text(query, "query")
        return self._encode(["query: " + query.strip()])[0]


@lru_cache(maxsize=1)
def get_embedding_service() -> EmbeddingService:
    """Servicio compartido por proceso; carga el modelo en la primera llamada.

    Si cambia la configuración, reiniciar el proceso o limpiar esta caché
    y la de get_settings. Las instancias explícitas también reutilizan modelo.
    """
    return EmbeddingService()
