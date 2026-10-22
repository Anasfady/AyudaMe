"""Conversation persistence — schema, factory and per-user isolation.

Covers `ui/persistence.py`: the SQLite adaptations of Chainlit's native
data layer (threads/steps saved per session user, reload-safe).
"""

from __future__ import annotations

import json
import sqlite3

import pytest

import ui.persistence as persistence
from chainlit.types import Pagination, ThreadFilter
from chainlit.user import User


def _tables(path) -> set:
    with sqlite3.connect(path) as con:
        rows = con.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
    return {row[0] for row in rows}


async def _layer(tmp_path):
    db = tmp_path / "chainlit.db"
    persistence.ensure_sqlite_schema(db)
    layer = persistence.SqliteDataLayer(conninfo=f"sqlite+aiosqlite:///{db.as_posix()}")
    return layer, db


class TestSchema:
    def test_creates_chainlit_tables(self, tmp_path):
        db = tmp_path / "t.db"
        persistence.ensure_sqlite_schema(db)
        assert {"users", "threads", "steps", "elements", "feedbacks"} <= _tables(db)

    def test_idempotent(self, tmp_path):
        db = tmp_path / "t.db"
        persistence.ensure_sqlite_schema(db)
        persistence.ensure_sqlite_schema(db)  # must not raise


class TestBuildDataLayer:
    def test_disabled_by_env(self, monkeypatch):
        monkeypatch.setenv("CHAINLIT_PERSISTENCE", "0")
        assert persistence.build_data_layer() is None

    @pytest.mark.asyncio
    async def test_enabled_bootstraps_schema(self, monkeypatch, tmp_path):
        db = tmp_path / "fresh.db"
        monkeypatch.setenv("CHAINLIT_PERSISTENCE", "1")
        monkeypatch.setenv("CHAINLIT_SQLITE_PATH", str(db))
        layer = persistence.build_data_layer()
        assert layer is not None
        assert db.exists()
        await layer.close()

    def test_app_registers_the_factory(self, monkeypatch):
        import ui.app  # noqa: F401 — registers @cl.data_layer on import

        from chainlit.config import config

        assert callable(config.code.data_layer)
        monkeypatch.setenv("CHAINLIT_PERSISTENCE", "0")
        assert config.code.data_layer() is None


class TestPerUserIsolation:
    @pytest.mark.asyncio
    async def test_threads_are_filtered_by_user(self, tmp_path):
        layer, _ = await _layer(tmp_path)
        pa = await layer.create_user(User(identifier="a@ejemplo.es", display_name="A"))
        pb = await layer.create_user(User(identifier="b@ejemplo.es", display_name="B"))
        await layer.update_thread(thread_id="t1", name="hilo de A", user_id=pa.id)

        page = Pagination(first=50)
        ra = await layer.list_threads(page, ThreadFilter(userId=pa.id))
        rb = await layer.list_threads(page, ThreadFilter(userId=pb.id))

        assert len(ra.data) == 1
        assert ra.data[0]["name"] == "hilo de A"
        assert rb.data == []
        await layer.close()

    @pytest.mark.asyncio
    async def test_list_threads_requires_a_user(self, tmp_path):
        layer, _ = await _layer(tmp_path)
        with pytest.raises(ValueError, match="userId is required"):
            await layer.list_threads(Pagination(first=50), ThreadFilter(userId=None))
        await layer.close()

    @pytest.mark.asyncio
    async def test_author_is_the_owner_identifier(self, tmp_path):
        layer, _ = await _layer(tmp_path)
        pa = await layer.create_user(User(identifier="a@ejemplo.es", display_name="A"))
        await layer.update_thread(thread_id="t2", name="hilo", user_id=pa.id)
        assert await layer.get_thread_author("t2") == "a@ejemplo.es"
        with pytest.raises(ValueError):
            await layer.get_thread_author("missing-thread")
        await layer.close()


class TestSqliteTags:
    @pytest.mark.asyncio
    async def test_list_tags_stored_as_json_and_decoded(self, tmp_path):
        layer, db = await _layer(tmp_path)
        pa = await layer.create_user(User(identifier="a@ejemplo.es", display_name="A"))
        await layer.update_thread(
            thread_id="t3", name="con tags", user_id=pa.id, tags=["irpf", "iva"]
        )

        with sqlite3.connect(db) as con:
            raw = con.execute('SELECT "tags" FROM threads WHERE "id" = ?', ("t3",)).fetchone()
        assert raw is not None and json.loads(raw[0]) == ["irpf", "iva"]

        page = Pagination(first=50)
        res = await layer.list_threads(page, ThreadFilter(userId=pa.id))
        assert res.data[0]["tags"] == ["irpf", "iva"]
        await layer.close()

    @pytest.mark.asyncio
    async def test_none_tags_stay_null(self, tmp_path):
        layer, db = await _layer(tmp_path)
        pa = await layer.create_user(User(identifier="a@ejemplo.es", display_name="A"))
        await layer.update_thread(thread_id="t4", name="sin tags", user_id=pa.id)
        with sqlite3.connect(db) as con:
            raw = con.execute('SELECT "tags" FROM threads WHERE "id" = ?', ("t4",)).fetchone()
        assert raw == (None,)
        await layer.close()
