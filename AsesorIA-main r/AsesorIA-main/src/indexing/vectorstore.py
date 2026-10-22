"""Chroma persistente con vectores explícitos y texto original para las citas."""
from __future__ import annotations

import hashlib
import json
from typing import Sequence

import chromadb
from chromadb.config import Settings as ChromaSettings

from src.common.schemas import ChunkMetadata
from src.common.settings import Settings, get_settings
from src.indexing.embeddings import EmbeddingService
from src.ingestion.chunking import Chunk


class VectorStore:
    """Acceso de infraestructura; no es una frontera de autorización de usuarios."""

    def __init__(self, settings: Settings, embedding_service: EmbeddingService | None = None):
        self._settings = settings
        self._embedding_service = embedding_service
        self.client = chromadb.PersistentClient(
            path=settings.chroma_dir, settings=ChromaSettings(anonymized_telemetry=False),
        )
        self.collection = self.client.get_or_create_collection(
            name=settings.chroma_collection, embedding_function=None,
            configuration={"hnsw": {"space": "cosine"}},
        )
        # get_or_create NO cambia la métrica de una colección existente.
        if self.collection.configuration.get("hnsw", {}).get("space") != "cosine":
            raise ValueError("La colección existente no usa cosine; utiliza otra colección")

    @property
    def embedding_service(self) -> EmbeddingService:
        # Abrir la colección no necesita descargar ni ejecutar el modelo.
        if self._embedding_service is None:
            self._embedding_service = EmbeddingService(self._settings)
        return self._embedding_service

    def add_chunks(self, chunks: Sequence[Chunk]) -> list[str]:
        """Upsert idempotente; devuelve los IDs en orden de entrada."""
        records = {}
        ids = []
        for chunk in chunks:
            if not isinstance(chunk, Chunk):
                raise TypeError("Se requieren Chunk con text y embedding_text separados")
            if not isinstance(chunk.text, str) or not chunk.text.strip():
                raise ValueError("El texto original del chunk no puede estar vacío")
            if not isinstance(chunk.embedding_text, str) or not chunk.embedding_text.strip():
                raise ValueError("embedding_text no puede estar vacío")
            metadata = ChunkMetadata.model_validate(chunk.metadata.model_dump()).to_store_dict()
            if metadata["source_scope"] == "private" and not str(metadata.get("session_id", "")).strip():
                raise ValueError("Los chunks privados requieren session_id")
            identity = [metadata["source_scope"], metadata.get("session_id"), metadata["doc_id"],
                        metadata["chunk_index"], chunk.start, chunk.end, chunk.text, chunk.embedding_text]
            chunk_id = hashlib.sha256(json.dumps(identity, ensure_ascii=False).encode("utf-8")).hexdigest()
            ids.append(chunk_id)
            records[chunk_id] = (chunk, metadata)
        # Deduplicar también dentro de una misma llamada: Chroma exige IDs únicos.
        entries = list(records.items())
        limit = self.client.get_max_batch_size()
        for offset in range(0, len(entries), limit):
            batch = entries[offset:offset + limit]
            vectors = self.embedding_service.embed_documents([record[0].embedding_text for _, record in batch])
            self.collection.upsert(
                ids=[key for key, _ in batch], embeddings=vectors,
                documents=[record[0].text for _, record in batch],
                metadatas=[record[1] for _, record in batch],
            )
        return ids

    def query(self, vector: list[float], *, top_k: int, filter_dict: dict | None = None) -> dict:
        """Consulta por vector; devuelve distancias cosine, no similitudes.

        API de infraestructura sin aislamiento de sesión. El retriever aplica
        la política de acceso de su sesión; no exponer este método directamente a usuarios.
        """
        if type(top_k) is not int or top_k <= 0:
            raise ValueError("top_k debe ser un entero positivo")
        count = self.collection.count()
        if count == 0:
            return {"documents": [[]], "metadatas": [[]], "distances": [[]]}
        return self.collection.query(
            query_embeddings=[vector], n_results=min(top_k, count),
            where=filter_dict or None, include=["documents", "metadatas", "distances"],
        )


def get_vectorstore(settings: Settings | None = None, *,
                    embedding_service: EmbeddingService | None = None) -> VectorStore:
    """Abre o crea la colección persistente configurada, sin embedding automático."""
    return VectorStore(settings or get_settings(), embedding_service)


def add_documents_to_vectorstore(chunks: Sequence[Chunk], *,
                                 vectorstore: VectorStore | None = None) -> list[str]:
    """Recibe Chunk, no Document: un Document pierde la separación de textos."""
    store = vectorstore if vectorstore is not None else get_vectorstore()
    return store.add_chunks(chunks)
