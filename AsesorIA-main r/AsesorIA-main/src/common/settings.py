"""Environment settings and YAML config loading."""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import yaml
from pydantic_settings import BaseSettings, SettingsConfigDict

# Configuración inicial V1; evaluada en nuestro corpus, no óptima universalmente.
DEFAULT_TOP_K = 8
DEFAULT_SCORE_THRESHOLD = 0.82

PROJECT_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    llm_provider: str = "anthropic"
    llm_model: str = ""
    llm_temperature: float = 0.0
    llm_timeout_seconds: int = 60
    ollama_base_url: str = "http://localhost:11434"

    embedding_model: str = "intfloat/multilingual-e5-base"
    # Valores asociados al modelo: revisar el prefijo si se cambia E5.
    embedding_passage_prefix: str = "passage: "
    embedding_max_tokens: int | None = None  # Por defecto, límite del tokenizer.

    # Configuración V1; permite overrides para otros experimentos.
    chunk_size_tokens: int | None = 256
    chunk_overlap_tokens: int | None = 32

    chroma_dir: str = str(PROJECT_ROOT / "chroma_db")
    chroma_collection: str = "corpus_256_32"

    api_base_url: str = "http://localhost:8000"
    asesoria_mock_api: int = 0


@lru_cache
def get_settings() -> Settings:
    return Settings()


@lru_cache
def load_config(name: str) -> dict:
    """Load config/<name>.yaml as a dict."""
    path = PROJECT_ROOT / "config" / f"{name}.yaml"
    with path.open(encoding="utf-8") as handle:
        return yaml.safe_load(handle)
