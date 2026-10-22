"""Logging helpers. Rule: never log the content of private documents or questions."""
from __future__ import annotations

import logging

_FORBIDDEN_KEYS = {"text", "content", "snippet", "question", "answer", "context"}


def setup_logging(level: int = logging.INFO) -> None:
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )


def log_event(logger: logging.Logger, event: str, **fields) -> None:
    """Log a structured event, silently dropping keys that could leak content."""
    safe = {k: v for k, v in fields.items() if k not in _FORBIDDEN_KEYS}
    logger.info("%s %s", event, safe)
