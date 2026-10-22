"""Conversation persistence — Chainlit native data layer on SQLite.

Scope: frontend integration only. The schema and the layer itself are
Chainlit's (`chainlit.data.sql_alchemy.SQLAlchemyDataLayer`); this module
adds the SQLite adaptations that upstream keeps PostgreSQL-only:

- DDL bootstrap (Chainlit ships queries but no schema creation),
- `tags` as JSON text (upstream binds Python lists, which SQLite rejects),
- no foreign keys (upstream's own issue #1788 workaround).

Ownership of the database (backups, migrations, Postgres) belongs to the
backend role — see `.agent-local/audit/product-ux/PERSISTENCE_HANDOFF.md`.
"""

from __future__ import annotations

import json
import os
import sqlite3
from pathlib import Path
from typing import Any, Optional

from chainlit.data.sql_alchemy import SQLAlchemyDataLayer

# One file per installation; separate deployments never share records.
DEFAULT_DB_PATH = Path(__file__).resolve().parent / ".data" / "chainlit.db"

# Official schema (docs.chainlit.io/data-layers/sqlalchemy) adapted to
# SQLite: UUID→TEXT, JSONB→TEXT, TEXT[]→TEXT, FK constraints dropped.
DDL = """
CREATE TABLE IF NOT EXISTS users (
  "id" TEXT PRIMARY KEY,
  "identifier" TEXT NOT NULL UNIQUE,
  "metadata" TEXT NOT NULL,
  "createdAt" TEXT
);
CREATE TABLE IF NOT EXISTS threads (
  "id" TEXT PRIMARY KEY,
  "createdAt" TEXT,
  "name" TEXT,
  "userId" TEXT,
  "userIdentifier" TEXT,
  "tags" TEXT,
  "metadata" TEXT
);
CREATE INDEX IF NOT EXISTS idx_threads_user ON threads ("userId");
CREATE TABLE IF NOT EXISTS steps (
  "id" TEXT PRIMARY KEY,
  "name" TEXT NOT NULL,
  "type" TEXT NOT NULL,
  "threadId" TEXT NOT NULL,
  "parentId" TEXT,
  "streaming" BOOLEAN NOT NULL,
  "waitForAnswer" BOOLEAN,
  "isError" BOOLEAN,
  "metadata" TEXT,
  "tags" TEXT,
  "input" TEXT,
  "output" TEXT,
  "createdAt" TEXT,
  "command" TEXT,
  "start" TEXT,
  "end" TEXT,
  "generation" TEXT,
  "showInput" TEXT,
  "language" TEXT,
  "indent" INTEGER,
  "defaultOpen" BOOLEAN,
  "modes" TEXT
);
CREATE INDEX IF NOT EXISTS idx_steps_thread ON steps ("threadId");
CREATE TABLE IF NOT EXISTS elements (
  "id" TEXT PRIMARY KEY,
  "threadId" TEXT,
  "type" TEXT,
  "url" TEXT,
  "chainlitKey" TEXT,
  "name" TEXT NOT NULL,
  "display" TEXT,
  "objectKey" TEXT,
  "size" TEXT,
  "page" INTEGER,
  "language" TEXT,
  "forId" TEXT,
  "mime" TEXT,
  "props" TEXT
);
CREATE TABLE IF NOT EXISTS feedbacks (
  "id" TEXT PRIMARY KEY,
  "forId" TEXT NOT NULL,
  "threadId" TEXT NOT NULL,
  "value" INTEGER NOT NULL,
  "comment" TEXT
);
"""


def ensure_sqlite_schema(path: Path | str) -> None:
    """Create the Chainlit schema if missing (idempotent, no side effects)."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(path) as con:
        con.executescript(DDL)


def _encode_tags(tags: Any) -> Any:
    if isinstance(tags, (list, tuple)):
        return json.dumps(list(tags), ensure_ascii=False)
    return tags


def _decode_tags(tags: Any) -> Any:
    if isinstance(tags, str) and tags:
        try:
            parsed = json.loads(tags)
        except ValueError:
            return tags
        return parsed if isinstance(parsed, list) else tags
    return tags


def _decode_thread(thread: Optional[dict]) -> Optional[dict]:
    if not thread:
        return thread
    if "tags" in thread:
        thread["tags"] = _decode_tags(thread.get("tags"))
    for step in thread.get("steps") or []:
        if isinstance(step, dict) and "tags" in step:
            step["tags"] = _decode_tags(step.get("tags"))
    return thread


class SqliteDataLayer(SQLAlchemyDataLayer):
    """Chainlit's SQLAlchemy layer with SQLite-safe tag handling."""

    async def update_thread(
        self,
        thread_id: str,
        name: Optional[str] = None,
        user_id: Optional[str] = None,
        metadata: Optional[dict] = None,
        tags: Optional[list] = None,
    ):
        return await super().update_thread(
            thread_id,
            name=name,
            user_id=user_id,
            metadata=metadata,
            tags=_encode_tags(tags),
        )

    async def create_step(self, step: dict):
        step = dict(step)
        if "tags" in step:
            step["tags"] = _encode_tags(step.get("tags"))
        return await super().create_step(step)

    async def update_step(self, step: dict):
        step = dict(step)
        if "tags" in step:
            step["tags"] = _encode_tags(step.get("tags"))
        return await super().update_step(step)

    async def get_thread(self, thread_id: str):
        return _decode_thread(await super().get_thread(thread_id))

    async def list_threads(self, pagination, filters):
        res = await super().list_threads(pagination, filters)
        for thread in res.data:
            _decode_thread(thread)
        return res


def build_data_layer() -> Optional[SqliteDataLayer]:
    """Factory registered with `@cl.data_layer`; Chainlit calls it lazily.

    Returns None (persistence off) when `CHAINLIT_PERSISTENCE=0`.
    """
    if os.environ.get("CHAINLIT_PERSISTENCE", "1") == "0":
        return None
    db_path = Path(os.environ.get("CHAINLIT_SQLITE_PATH") or DEFAULT_DB_PATH)
    ensure_sqlite_schema(db_path)
    return SqliteDataLayer(conninfo=f"sqlite+aiosqlite:///{db_path.absolute().as_posix()}")
