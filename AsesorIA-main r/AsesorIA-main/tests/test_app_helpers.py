"""Tests for pure helper logic in ui/app.py (no Chainlit server needed)."""

from pathlib import Path
from types import SimpleNamespace

import pytest

import ui.app as app


class TestValidateFiles:
    def test_valid_pdf(self, tmp_path):
        path = tmp_path / "doc.pdf"
        path.write_bytes(b"%PDF-1.4 test")
        valid, errors = app._validate_files([("doc.pdf", str(path))])
        assert valid == [("doc.pdf", str(path))]
        assert errors == []

    def test_valid_markdown(self, tmp_path):
        path = tmp_path / "notas.md"
        path.write_text("# Hola")
        valid, errors = app._validate_files([("notas.md", str(path))])
        assert valid == [("notas.md", str(path))]
        assert errors == []

    def test_wrong_extension(self, tmp_path):
        path = tmp_path / "ejecutable.exe"
        path.write_bytes(b"MZ")
        valid, errors = app._validate_files([("ejecutable.exe", str(path))])
        assert valid == []
        assert len(errors) == 1
        assert "No puedo aceptar" in errors[0]

    def test_missing_file(self, tmp_path):
        valid, errors = app._validate_files([("perdido.pdf", str(tmp_path / "no.pdf"))])
        assert valid == []
        assert "No se ha podido leer" in errors[0]

    def test_empty_file(self, tmp_path):
        path = tmp_path / "vacio.pdf"
        path.write_bytes(b"")
        valid, errors = app._validate_files([("vacio.pdf", str(path))])
        assert valid == []
        assert "vacío" in errors[0]

    def test_mixed_batch_keeps_valid_files(self, tmp_path):
        good = tmp_path / "bueno.pdf"
        good.write_bytes(b"%PDF")
        bad = tmp_path / "malo.exe"
        bad.write_bytes(b"MZ")
        valid, errors = app._validate_files(
            [("bueno.pdf", str(good)), ("malo.exe", str(bad))]
        )
        assert valid == [("bueno.pdf", str(good))]
        assert len(errors) == 1

    def test_keeps_original_display_name(self, tmp_path):
        # Chainlit stores the file as <uuid>.pdf: the name the user
        # sees must be the original, not the storage name.
        path = tmp_path / "aaaa-bbbb.pdf"
        path.write_bytes(b"%PDF")
        valid, _ = app._validate_files([("manual-iva-2025.pdf", str(path))])
        assert valid == [("manual-iva-2025.pdf", str(path))]


class TestPlural:
    def test_singular(self):
        assert app._plural(1, "fragmento") == "1 fragmento"

    def test_plural(self):
        assert app._plural(3, "fragmento") == "3 fragmentos"


class TestUploadCommandMatching:
    def test_upload_commands_are_exact(self):
        # Matching is exact after normalization: questions are not hijacked.
        assert "cargar" in app.UPLOAD_COMMANDS
        assert "cargar documentos" in app.UPLOAD_COMMANDS
        # Legitimate questions containing the word are NOT commands.
        assert "¿qué gastos puedo cargar en el libro?" not in app.UPLOAD_COMMANDS


class TestSuggestionActions:
    def test_fresh_conversation_has_spanish_actions(self):
        actions = app._suggestion_actions(asked=False)
        assert actions is not None
        assert len(actions) == len(app.SUGGESTION_QUESTIONS)
        for action in actions:
            assert action.payload["intent"] == "question"
            assert action.payload["text"].strip()
            assert action.label.startswith("💡 ")
            for forbidden in ("Step", "Backend", "Retriever", "Executing"):
                assert forbidden not in action.label

    def test_suppressed_after_first_question(self):
        assert app._suggestion_actions(asked=True) is None

    def test_names_are_unique(self):
        actions = app._suggestion_actions(asked=False)
        names = [a.name for a in actions]
        assert len(set(names)) == len(names)


class TestEmitTask:
    @pytest.mark.asyncio
    async def test_emits_start_and_end(self, monkeypatch):
        calls: list[str] = []

        class Emitter:
            async def task_start(self):
                calls.append("start")

            async def task_end(self):
                calls.append("end")

        monkeypatch.setattr(
            app.cl, "context", SimpleNamespace(emitter=Emitter()), raising=False
        )
        await app._emit_task("start")
        await app._emit_task("end")
        assert calls == ["start", "end"]

    @pytest.mark.asyncio
    async def test_swallows_emitter_errors(self, monkeypatch):
        class Emitter:
            async def task_start(self):
                raise RuntimeError("boom")

            async def task_end(self):
                raise RuntimeError("boom")

        monkeypatch.setattr(
            app.cl, "context", SimpleNamespace(emitter=Emitter()), raising=False
        )
        await app._emit_task("start")
        await app._emit_task("end")


class TestActionCallbacksBalance:
    @pytest.mark.asyncio
    async def test_load_documents_wraps_start_end(self, monkeypatch):
        calls: list[str] = []

        async def fake_ask():
            calls.append("ask")

        async def fake_emit(kind: str):
            calls.append(kind)

        monkeypatch.setattr(app, "_ask_for_files", fake_ask)
        monkeypatch.setattr(app, "_emit_task", fake_emit)
        await app._on_load_documents(action=None)
        assert calls == ["start", "ask", "end"]

    @pytest.mark.asyncio
    async def test_load_documents_ends_even_if_ask_fails(self, monkeypatch):
        calls: list[str] = []

        async def fake_ask():
            calls.append("ask")
            raise RuntimeError("x")

        async def fake_emit(kind: str):
            calls.append(kind)

        monkeypatch.setattr(app, "_ask_for_files", fake_ask)
        monkeypatch.setattr(app, "_emit_task", fake_emit)
        with pytest.raises(RuntimeError):
            await app._on_load_documents(action=None)
        assert calls == ["start", "ask", "end"]

    @pytest.mark.asyncio
    async def test_suggestion_uses_payload_text(self, monkeypatch):
        calls: list[object] = []

        class FakeMessage:
            def __init__(self, **kwargs):
                calls.append(kwargs.get("content"))

            async def send(self):
                return self

        async def fake_answer(question: str):
            calls.append(("answer", question))

        async def fake_emit(kind: str):
            calls.append(("emit", kind))

        monkeypatch.setattr(app.cl, "Message", FakeMessage, raising=False)
        monkeypatch.setattr(app, "_answer_question", fake_answer)
        monkeypatch.setattr(app, "_emit_task", fake_emit)
        question = "¿Qué es el IVA soportado?"
        await app._on_suggestion(SimpleNamespace(payload={"text": question}))
        assert calls == [
            ("emit", "start"),
            question,
            ("answer", question),
            ("emit", "end"),
        ]

    @pytest.mark.asyncio
    async def test_suggestion_without_text_is_noop(self, monkeypatch):
        calls: list[str] = []

        async def fake_emit(kind: str):
            calls.append(kind)

        monkeypatch.setattr(app, "_emit_task", fake_emit)
        await app._on_suggestion(SimpleNamespace(payload={"text": "   "}))
        assert calls == []


class TestSessionId:
    def test_stable_fallback_outside_chainlit_context(self):
        # Unit tests have no websocket context: the process-wide id is used
        # and it must be stable between calls (never None/empty).
        first = app._session_id()
        second = app._session_id()
        assert isinstance(first, str) and first
        assert first == second

    def test_uses_chainlit_session_id_when_available(self, monkeypatch):
        session = SimpleNamespace(id="ws-sesion-42")
        monkeypatch.setattr(
            app.cl, "context", SimpleNamespace(session=session), raising=False
        )
        assert app._session_id() == "ws-sesion-42"


class TestAmbiguousQueries:
    def test_vague_openers_are_ambiguous(self):
        for question in (
            "hola",
            "¡ayuda!",
            "¿qué puedo preguntar?",
            "no sé",
            "explícame",
            "buenas tardes",
            "Gracias.",
        ):
            assert app.is_ambiguous(question) is True, question

    def test_conversational_meta_queries_are_ambiguous(self):
        # Regression: these used to reach the RAG and always got the same
        # generic answer.
        for question in (
            "ME PUEDES GUIAR?",
            "QUE ME PUEDES DECIR?",
            "algo mas?",
            "ayuda",
            "¿Qué puedo preguntar?",
            "no sé qué preguntar",
            "No sé qué decir.",
        ):
            assert app.is_ambiguous(question) is True, question

    def test_concrete_and_broad_legitimate_queries_are_not(self):
        for question in (
            "explícame el IVA",
            "IRPF",
            "¿Qué gastos son deducibles de un autónomo?",
            "¿cuándo se presenta el modelo 303?",
            "hola, ¿qué gastos son deducibles?",
        ):
            assert app.is_ambiguous(question) is False, question

    def test_valid_queries_never_blocked_by_meta_words(self):
        # Regression: whole-message matching must not swallow valid queries
        # that merely contain meta words («ayuda», «me puedes guiar»…).
        for question in (
            "Explícame el IVA",
            "¿Qué me puedes decir sobre las retenciones?",
            "Necesito ayuda con el modelo 303",
            "¿Me puedes guiar con el alta de autónomo?",
        ):
            assert app.is_ambiguous(question) is False, question

    def test_blank_input_is_not_ambiguous(self):
        # Blank has its own dedicated state before this rule (§1).
        assert app.is_ambiguous("") is False
        assert app.is_ambiguous("   ") is False


class TestGuidanceRouting:
    """Ambiguous queries never reach the RAG; legitimate ones always do."""

    @staticmethod
    def _patch(monkeypatch, notified: list, answered: list):
        async def fake_notify(text, actions=None):
            notified.append((text, actions))

        async def fake_answer(question):
            answered.append(question)

        monkeypatch.setattr(app, "_notify", fake_notify)
        monkeypatch.setattr(app, "_answer_question", fake_answer)
        monkeypatch.setattr(app, "_get_documents", lambda: [])
        monkeypatch.setattr(app, "_has_asked", lambda: False)

    @pytest.mark.asyncio
    async def test_hola_shows_guidance_instead_of_rag(self, monkeypatch):
        notified: list = []
        answered: list = []
        self._patch(monkeypatch, notified, answered)

        await app._handle_message(SimpleNamespace(content="hola"))

        assert answered == []
        assert len(notified) == 1
        text, actions = notified[0]
        assert "**Claro. Puedo ayudarte a consultar la documentación disponible.**" in text
        assert "**¿Qué te interesa?**" in text
        assert len(actions) == 5
        labels = [a.label for a in actions]
        assert labels == [
            "Alta de autónomo",
            "IVA",
            "IRPF",
            "Gastos deducibles",
            "Obligaciones fiscales",
        ]

    @pytest.mark.asyncio
    async def test_guidance_suggestions_are_real_actions(self, monkeypatch):
        # Regression: every suggestion button must carry a question payload
        # so clicking it runs the normal RAG flow (not decoration).
        notified: list = []
        answered: list = []
        self._patch(monkeypatch, notified, answered)

        await app._handle_message(SimpleNamespace(content="ayuda"))

        assert answered == []
        _, actions = notified[0]
        for action in actions:
            payload = action.payload or {}
            assert payload.get("intent") == "question"
            assert str(payload.get("text") or "").strip()
            assert action.name.startswith("orientacion_")

    @pytest.mark.asyncio
    async def test_new_meta_queries_route_to_guidance(self, monkeypatch):
        # Regression: these used to go to the mock and get the generic reply.
        for question in ("ME PUEDES GUIAR?", "QUE ME PUEDES DECIR?", "algo mas?"):
            notified: list = []
            answered: list = []
            self._patch(monkeypatch, notified, answered)

            await app._handle_message(SimpleNamespace(content=question))

            assert answered == [], question
            assert notified and "Claro." in notified[0][0], question

    @pytest.mark.asyncio
    async def test_explícame_alone_shows_guidance(self, monkeypatch):
        notified: list = []
        answered: list = []
        self._patch(monkeypatch, notified, answered)

        await app._handle_message(SimpleNamespace(content="explícame"))

        assert answered == []
        assert notified and "Claro." in notified[0][0]

    @pytest.mark.asyncio
    async def test_broad_but_legitimate_query_reaches_the_rag(self, monkeypatch):
        notified: list = []
        answered: list = []
        self._patch(monkeypatch, notified, answered)

        await app._handle_message(SimpleNamespace(content="Explícame el IVA"))

        assert answered == ["Explícame el IVA"]
        assert notified == []

    @pytest.mark.asyncio
    async def test_concrete_question_reaches_the_rag(self, monkeypatch):
        notified: list = []
        answered: list = []
        self._patch(monkeypatch, notified, answered)

        question = "¿Qué es el IVA soportado y cómo se deduce?"
        await app._handle_message(SimpleNamespace(content=question))

        assert answered == [question]
        assert notified == []

    @pytest.mark.asyncio
    async def test_guidance_is_contextual_with_uploaded_documents(self, monkeypatch):
        notified: list = []
        answered: list = []
        self._patch(monkeypatch, notified, answered)
        monkeypatch.setattr(app, "_get_documents", lambda: ["ruta/doc.pdf"])

        await app._handle_message(SimpleNamespace(content="ayuda"))

        assert answered == []
        assert "documentación cargada" in notified[0][0]

    @pytest.mark.asyncio
    async def test_guidance_reduces_suggestions_mid_conversation(self, monkeypatch):
        notified: list = []
        answered: list = []
        self._patch(monkeypatch, notified, answered)
        monkeypatch.setattr(app, "_has_asked", lambda: True)

        await app._handle_message(SimpleNamespace(content="no sé"))

        assert answered == []
        text, actions = notified[0]
        assert "Sigue preguntando" in text
        assert len(actions) == 2

    @pytest.mark.asyncio
    async def test_upload_command_is_not_treated_as_ambiguous(self, monkeypatch):
        notified: list = []
        answered: list = []
        asked: list = []

        async def fake_notify(text, actions=None):
            notified.append(text)

        async def fake_answer(question):
            answered.append(question)

        async def fake_ask():
            asked.append(True)

        monkeypatch.setattr(app, "_notify", fake_notify)
        monkeypatch.setattr(app, "_answer_question", fake_answer)
        monkeypatch.setattr(app, "_ask_for_files", fake_ask)

        await app._handle_message(SimpleNamespace(content="cargar"))

        assert asked == [True]
        assert answered == []
        assert notified == []


class TestAskFileCopy:
    @pytest.mark.asyncio
    async def test_ask_file_content_is_clean_and_informative(self, monkeypatch):
        captured: dict = {}

        class FakeAskFile:
            def __init__(self, content=None, **kwargs):
                captured["content"] = content

            async def send(self):
                return []

        async def fake_notify(text, actions=None):
            captured.setdefault("notified", []).append(text)

        monkeypatch.setattr(app.cl, "AskFileMessage", FakeAskFile)
        monkeypatch.setattr(app, "_notify", fake_notify)

        await app._ask_for_files()

        content = captured["content"]
        assert "Adjunta la documentación" in content
        assert "PDF, TXT o Markdown" in content
        # FASE 12 (brief Persona 4): the workaround notice is gone for good.
        assert "cierra solo" not in content
        # Regression: no meta commentary in the normal flow.
        assert "equivocado" not in content
        # No file selected → friendly state, no error.
        assert captured["notified"]


class TestNormalFlowMessages:
    def test_app_does_not_emit_stop_notice_or_meta_commentary(self):
        # Regression: «Consulta detenida» only exists as the translation of
        # Chainlit's real stop notice (custom.js, shown ONLY on a real
        # stop); «¿Te has equivocado de botón?» was meta commentary removed
        # from the guided upload.
        source = Path(app.__file__).read_text(encoding="utf-8")
        assert "Consulta detenida" not in source
        assert "equivocado de botón" not in source

    def test_custom_js_localizes_only_the_real_stop_notice(self):
        js_dir = Path(app.__file__).parent / "public"
        js = (js_dir / "custom.js").read_text(encoding="utf-8")
        assert "Task manually stopped." in js
        assert "Consulta detenida" in js
        # The «Usado/Usando» internal chip stays hidden via CSS.
        css = (js_dir / "custom.css").read_text(encoding="utf-8")
        assert '[id^="step-"] > span:first-child' in css
        assert "display: none" in css
