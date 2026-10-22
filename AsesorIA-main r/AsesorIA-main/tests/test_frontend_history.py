"""Conversational history transport contract — UI → adapter boundary.

Persona 4 scope ONLY: build (``app._build_history``), validate/limit
(``rag_adapter.normalize_history``) and transport (``RagAdapter.ask(...,
history=)``). No backend behaviour, no query rewriting, no answering logic —
those belong to Backend/RAG (see docs/ux-ui-architecture.md §10).

The full chain (``_handle_message`` → ``_answer_question``) needs a live
Chainlit context (``cl.Step`` / ``cl.user_session``); the contract seam where
history actually travels is ``_build_history(question)`` → ``ask(...,
history=)``, which is what these tests exercise without a running server.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

import ui.app as app
from ui.rag_adapter import HISTORY_WINDOW, RagAdapter, normalize_history


def _turn(kind: str, content: str, notice: bool = False) -> SimpleNamespace:
    """Chat-context-like message (public attrs used by _build_history)."""
    return SimpleNamespace(
        type=kind,
        content=content,
        metadata={"ias_ui_notice": True} if notice else None,
    )


class LegacyBackend:
    """Current real pipeline shape: ``answer_query(question)`` only."""

    def __init__(self) -> None:
        self.calls: list[str] = []

    async def answer_query(self, question: str) -> dict:
        self.calls.append(question)
        return {"answer": "ok", "source_documents": []}


class HistoryBackend:
    """Future backend shape: ``answer_query(question, history=None)``."""

    def __init__(self) -> None:
        self.calls: list[dict] = []

    async def answer_query(self, question: str, history=None) -> dict:
        self.calls.append({"question": question, "history": history})
        return {"answer": "ok", "source_documents": []}


class TestHistoryContract:
    """TESTS 1-6: retrocompatibility, transport, order, validation, window."""

    @pytest.mark.asyncio
    async def test_1_call_without_history_still_works(self):
        """Legacy positional call + implicit history=None are equivalent."""
        legacy = LegacyBackend()
        await RagAdapter(backend=legacy).ask("q", ["doc.pdf"], ["doc.pdf"])

        future = HistoryBackend()
        await RagAdapter(backend=future).ask("q", ["doc.pdf"], ["doc.pdf"])

        assert legacy.calls == ["q"]
        assert future.calls == [{"question": "q", "history": None}]

    @pytest.mark.asyncio
    async def test_1b_legacy_backend_never_gets_history_kwarg(self):
        """A backend whose signature lacks `history` must not receive it."""
        legacy = LegacyBackend()
        await RagAdapter(backend=legacy).ask(
            "q", ["doc.pdf"], ["doc.pdf"], history=[{"role": "user", "content": "x"}]
        )
        assert legacy.calls == ["q"]  # no TypeError, nothing forwarded

    @pytest.mark.asyncio
    async def test_2_valid_history_is_transported(self):
        history = [
            {"role": "user", "content": "pregunta 1"},
            {"role": "assistant", "content": "respuesta 1"},
        ]
        backend = HistoryBackend()
        await RagAdapter(backend=backend).ask("q2", [], [], history=history)
        assert backend.calls[-1]["history"] == history

    @pytest.mark.asyncio
    async def test_3_chronological_order_preserved(self):
        history = [
            {"role": "user", "content": "user 1"},
            {"role": "assistant", "content": "assistant 1"},
            {"role": "user", "content": "user 2"},
            {"role": "assistant", "content": "assistant 2"},
        ]
        backend = HistoryBackend()
        await RagAdapter(backend=backend).ask("q", [], [], history=history)
        received = backend.calls[-1]["history"]
        assert [e["content"] for e in received] == [
            "user 1",
            "assistant 1",
            "user 2",
            "assistant 2",
        ]
        assert [e["role"] for e in received] == [
            "user",
            "assistant",
            "user",
            "assistant",
        ]

    @pytest.mark.asyncio
    async def test_4_invalid_roles_are_dropped(self):
        history = [
            {"role": "user", "content": "válida"},
            {"role": "system", "content": "ignorada"},
            {"role": "tool", "content": "ignorada"},
            {"role": "foo", "content": "ignorada"},
        ]
        backend = HistoryBackend()
        await RagAdapter(backend=backend).ask("q", [], [], history=history)
        assert backend.calls[-1]["history"] == [{"role": "user", "content": "válida"}]

    def test_5_malformed_entries_policy(self):
        """Deterministic policy: invalid input → dropped / None, never raises."""
        assert normalize_history(None) is None
        assert normalize_history([]) == []
        assert normalize_history("texto") is None
        assert normalize_history(42) is None

        mixed = [
            {"role": "user"},             # no content → dropped
            {"content": "hola"},          # no role → dropped
            "texto",                      # not a dict → dropped
            None,                         # not a dict → dropped
            {"role": "user", "content": "   "},      # blank → dropped
            {"role": "user", "content": {"a": 1}},   # structural → dropped
            {"role": "assistant", "content": "buenas"},
        ]
        assert normalize_history(mixed) == [
            {"role": "assistant", "content": "buenas"}
        ]

        # scalar content is safely stringified (documented policy)
        assert normalize_history([{"role": "user", "content": 123}]) == [
            {"role": "user", "content": "123"}
        ]

    def test_6_window_keeps_last_messages(self):
        history = [
            {"role": "user" if i % 2 == 0 else "assistant", "content": f"m{i}"}
            for i in range(HISTORY_WINDOW + 10)
        ]
        out = normalize_history(history)
        assert out is not None
        assert len(out) == HISTORY_WINDOW
        assert out[0]["content"] == "m10"  # oldest kept = window start
        assert out[-1]["content"] == f"m{HISTORY_WINDOW + 9}"  # newest kept


class TestBuildHistory:
    """TESTS 7-9 (+ isolation): app-level construction from cl.chat_context."""

    def test_7_current_question_is_not_duplicated(self, monkeypatch):
        context = [
            _turn("user_message", "hola"),
            _turn("assistant_message", "buenas"),
            _turn("user_message", "¿Entonces tengo que hacerlo presencial?"),
        ]
        monkeypatch.setattr(app.cl.chat_context, "get", lambda: list(context))
        history = app._build_history("¿Entonces tengo que hacerlo presencial?")
        assert [e["content"] for e in history] == ["hola", "buenas"]
        assert "¿Entonces tengo que hacerlo presencial?" not in [
            e["content"] for e in history
        ]

    def test_7b_repeated_question_keeps_only_prior_occurrences(self, monkeypatch):
        context = [
            _turn("user_message", "misma"),
            _turn("assistant_message", "r"),
            _turn("user_message", "misma"),  # in-flight → removed once
        ]
        monkeypatch.setattr(app.cl.chat_context, "get", lambda: list(context))
        history = app._build_history("misma")
        assert [e["content"] for e in history] == ["misma", "r"]

    def test_7c_ui_notices_and_nontext_turns_are_excluded(self, monkeypatch):
        context = [
            _turn("assistant_message", "Bienvenida (chrome)", notice=True),
            _turn("user_message", ""),
            _turn("task_step", "tarea"),          # non-message type
            _turn("user_message", "pregunta real"),
            _turn("assistant_message", "respuesta real"),
        ]
        monkeypatch.setattr(app.cl.chat_context, "get", lambda: list(context))
        history = app._build_history("otra cosa")
        assert [e["content"] for e in history] == [
            "pregunta real",
            "respuesta real",
        ]

    def test_8_sessions_do_not_share_history(self, monkeypatch):
        """No process-level cache: each build reads the (per-session) source."""
        session_a = [_turn("user_message", "A1"), _turn("assistant_message", "AA1")]
        monkeypatch.setattr(app.cl.chat_context, "get", lambda: list(session_a))
        history_a = app._build_history("x")

        session_b = [_turn("user_message", "B1")]
        monkeypatch.setattr(app.cl.chat_context, "get", lambda: list(session_b))
        history_b = app._build_history("x")

        assert history_a != history_b
        assert "A1" not in str(history_b)

    @pytest.mark.asyncio
    async def test_8b_adapter_caches_nothing_between_calls(self):
        """A fresh conversation (history omitted) must not inherit the old one."""
        backend = HistoryBackend()
        adapter = RagAdapter(backend=backend)
        await adapter.ask("q1", [], [], history=[{"role": "user", "content": "A"}])
        await adapter.ask("q2", [], [])
        assert backend.calls[0]["history"] is not None
        assert backend.calls[1]["history"] is None

    @pytest.mark.asyncio
    async def test_9_chain_ui_builds_and_adapter_transports(self, monkeypatch):
        """message → _build_history → adapter.ask(..., history=...)."""
        context = [
            _turn("user_message", "¿Cuándo hay que darse de alta como autónomo?"),
            _turn("assistant_message", "Modelo 036/037…"),
            _turn("user_message", "¿Y si además tengo un trabajo por cuenta ajena?"),
        ]
        current = "¿Y si además tengo un trabajo por cuenta ajena?"
        monkeypatch.setattr(app.cl.chat_context, "get", lambda: list(context))

        history = app._build_history(current)
        backend = HistoryBackend()
        await RagAdapter(backend=backend).ask(current, [], [], history=history)

        assert backend.calls[-1]["question"] == current
        assert backend.calls[-1]["history"] == [
            {"role": "user", "content": "¿Cuándo hay que darse de alta como autónomo?"},
            {"role": "assistant", "content": "Modelo 036/037…"},
        ]

    def test_build_history_without_session_returns_none(self):
        """No Chainlit context (unit tests/startup) → guarded None, no crash."""
        assert app._build_history("x") is None


class TestNegativeNoFakedMemory:
    """§13: the UI TRANSPORTS context; it never resolves or rewrites it."""

    def test_ui_does_not_rewrite_history_contents(self):
        original = [
            {"role": "user", "content": "¿Y entonces cuándo tengo que presentarlo?"},
        ]
        out = normalize_history(original)
        assert out == original  # byte-identical: no contextualization in UI

    @pytest.mark.asyncio
    async def test_ui_does_not_answer_follow_ups_by_itself(self):
        """Transport only: the reply still comes from the backend/mock path."""
        backend = HistoryBackend()
        adapter = RagAdapter(backend=backend)
        response = await adapter.ask(
            "¿Y entonces cuándo tengo que presentarlo?",
            [],
            [],
            history=[{"role": "user", "content": "¿Qué modelo tengo que presentar?"}],
        )
        assert response.answer == "ok"  # produced by the backend, not the UI
