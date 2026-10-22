"""Unit tests for frontend contract normalization and formatters.

These tests run synchronously without starting Chainlit.
"""

import pytest

from ui.contracts import RAGResponse, Source
from ui.formatters import (
    format_answer,
    format_answer_block,
    format_clarify,
    format_documents_state,
    format_empty_question,
    format_error,
    format_error_message,
    format_file_error,
    format_metadata,
    format_no_answer,
    format_no_documents,
    format_question_too_long,
    format_source,
    format_source_header,
    format_source_quote,
    format_sources,
    format_sources_block,
    format_welcome,
)
from ui.rag_adapter import RagAdapter
from ui.mock_rag import MockRAG


# --------------------------------------------------------------------------- #
# Contracts
# --------------------------------------------------------------------------- #


class TestSource:
    def test_source_from_dict(self):
        data = {
            "document": "Doc.pdf",
            "content": "Fragmento",
            "page": 10,
            "section": "Intro",
            "score": 0.85,
            "metadata": {"key": "val"},
        }
        src = Source.from_dict(data)
        assert src.document == "Doc.pdf"
        assert src.content == "Fragmento"
        assert src.page == 10
        assert src.section == "Intro"
        assert src.score == 0.85
        assert src.metadata == {"key": "val"}

    def test_source_from_dict_with_missing_keys(self):
        data = {"document": "Doc.pdf", "content": "Fragmento"}
        src = Source.from_dict(data)
        assert src.page is None
        assert src.section is None
        assert src.score is None
        assert src.metadata is None

    def test_source_from_any_with_source(self):
        src1 = Source(document="Doc.pdf", content="Frag")
        src2 = Source.from_any(src1)
        assert src2 is src1

    def test_source_from_any_with_dict(self):
        data = {"document": "Doc.pdf", "content": "Frag", "page": 1}
        src = Source.from_any(data)
        assert src.document == "Doc.pdf"
        assert src.page == 1

    def test_source_from_any_with_plain_string(self):
        src = Source.from_any("just text")
        assert src.document == "unknown"
        assert src.content == "just text"


class TestRAGResponse:
    def test_response_from_dict_with_full_sources(self):
        data = {
            "answer": "Respuesta de prueba",
            "sources": [
                {"document": "Doc1.pdf", "content": "Frag1", "page": 1},
                {"document": "Doc2.pdf", "content": "Frag2", "page": 2},
            ],
            "grounded": True,
            "no_answer_reason": None,
            "latency_ms": 100.0,
        }
        resp = RAGResponse.from_dict(data)
        assert resp.answer == "Respuesta de prueba"
        assert resp.grounded is True
        assert len(resp.sources) == 2
        assert resp.has_answer
        assert resp.has_sources

    def test_response_from_dict_with_empty_sources(self):
        data = {
            "answer": "",
            "sources": [],
            "grounded": False,
            "no_answer_reason": "no data",
        }
        resp = RAGResponse.from_dict(data)
        assert resp.has_answer is False
        assert resp.has_sources is False
        assert resp.grounded is False
        assert resp.no_answer_reason == "no data"

    def test_response_from_dict_with_none_sources(self):
        data = {"answer": "", "sources": None, "grounded": False}
        resp = RAGResponse.from_dict(data)
        assert resp.sources == []
        assert resp.has_sources is False

    def test_response_from_any_with_response(self):
        resp1 = RAGResponse(answer="test")
        resp2 = RAGResponse.from_any(resp1)
        assert resp2 is resp1

    def test_response_from_any_with_string(self):
        resp = RAGResponse.from_any("just a string")
        assert resp.answer == "just a string"
        assert resp.grounded is False

    def test_sources_with_incomplete_metadata(self):
        data = {
            "answer": "Test",
            "sources": [{"document": "Doc.pdf", "content": "Frag"}],
            "grounded": True,
        }
        resp = RAGResponse.from_dict(data)
        assert resp.sources[0].page is None
        assert resp.sources[0].section is None
        assert resp.sources[0].score is None

    def test_response_with_no_answer_reason(self):
        data = {
            "answer": "",
            "sources": [],
            "grounded": False,
            "no_answer_reason": "No relevant info",
        }
        resp = RAGResponse.from_dict(data)
        assert resp.grounded is False
        assert resp.no_answer_reason == "No relevant info"


# --------------------------------------------------------------------------- #
# Formatters — sources
# --------------------------------------------------------------------------- #


class TestFormatSourceHeader:
    def test_with_all_fields(self):
        src = Source(
            document="Doc.pdf",
            content="Contenido relevante",
            page=42,
            section="Introducción",
            score=0.95,
        )
        header = format_source_header(src, index=1)
        assert "**1. Doc.pdf**" in header
        assert "pág. 42" in header
        assert "Introducción" in header
        assert "relevancia 0,95" in header

    def test_without_index(self):
        src = Source(document="Doc.pdf", content="Contenido", page=1)
        header = format_source_header(src)
        assert "**Doc.pdf**" in header
        assert "1." not in header

    def test_missing_page_is_omitted(self):
        src = Source(document="Doc.pdf", content="Contenido", page=None)
        header = format_source_header(src)
        assert "pág." not in header
        assert "no disponible" not in header

    def test_missing_section_is_omitted(self):
        src = Source(document="Doc.pdf", content="Contenido", page=1, section=None)
        header = format_source_header(src)
        assert "pág. 1" in header
        assert "no disponible" not in header

    def test_header_without_any_metadata_is_label_only(self):
        src = Source(document="Doc.pdf", content="Contenido")
        assert format_source_header(src, index=2) == "**2. Doc.pdf**"

    def test_missing_score_is_omitted(self):
        src = Source(document="Doc.pdf", content="Contenido", page=1, score=None)
        assert "relevancia" not in format_source_header(src)

    def test_missing_document_placeholder(self):
        src = Source(document="", content="Contenido")
        assert "Documento desconocido" in format_source_header(src)


class TestFormatSourceQuote:
    def test_with_content(self):
        src = Source(document="Doc.pdf", content="Contenido legal")
        quote = format_source_quote(src)
        assert quote.startswith("> ")
        assert "Contenido legal" in quote

    def test_with_empty_content(self):
        src = Source(document="Doc.pdf", content="")
        assert "(fragmento no disponible)" in format_source_quote(src)


class TestFormatSource:
    def test_header_plus_quote(self):
        src = Source(document="Doc.pdf", content="Frag", page=3)
        result = format_source(src, index=1)
        lines = result.splitlines()
        assert "**1. Doc.pdf**" in lines[0]
        assert lines[1].startswith("> ")

    def test_empty_content_still_renders(self):
        src = Source(document="Doc.pdf", content="")
        result = format_source(src)
        assert "Doc.pdf" in result
        assert "(fragmento no disponible)" in result


class TestFormatMetadata:
    def test_with_complete_data(self):
        src = Source(document="Doc.pdf", content="Fragmento", page=1, section="Intro")
        result = format_metadata(src)
        assert "Doc.pdf" in result
        assert "pág. 1" in result
        assert "Intro" in result

    def test_with_missing_fields(self):
        src = Source(document="Doc.pdf", content="Fragmento", page=None, section=None)
        assert format_metadata(src) == "Doc.pdf"

    def test_with_empty_document(self):
        src = Source(document="", content="Fragmento", page=None, section=None)
        assert format_metadata(src) == "Origen desconocido"


class TestFormatSources:
    def test_empty_list_returns_empty(self):
        assert format_sources([]) == ""

    def test_multiple_sources_are_numbered(self):
        srcs = [
            Source(document="Doc1.pdf", content="Frag1", page=1),
            Source(document="Doc2.pdf", content="Frag2", page=2),
        ]
        result = format_sources(srcs)
        assert "**1. Doc1.pdf**" in result
        assert "**2. Doc2.pdf**" in result

    def test_block_with_title(self):
        srcs = [Source(document="Doc.pdf", content="Frag", page=1)]
        block = format_sources_block(srcs)
        assert "Fuentes utilizadas · 1" in block
        assert "Doc.pdf" in block

    def test_block_without_sources_is_empty(self):
        assert format_sources_block([]) == ""

    def test_block_counts_three_sources(self):
        srcs = [Source(document=f"D{i}.pdf", content="c") for i in range(3)]
        block = format_sources_block(srcs)
        assert "Fuentes utilizadas · 3" in block


# --------------------------------------------------------------------------- #
# Formatters — answer
# --------------------------------------------------------------------------- #


class TestFormatAnswer:
    def test_answer_is_stripped(self):
        resp = RAGResponse(answer="  Respuesta  ")
        assert format_answer(resp) == "Respuesta"

    def test_answer_block_with_sources(self):
        resp = RAGResponse(
            answer="Respuesta",
            sources=[Source(document="Doc.pdf", content="Frag", page=1)],
        )
        block = format_answer_block(resp)
        assert "Respuesta" in block
        assert "Fuentes utilizadas" in block
        assert "Doc.pdf" in block

    def test_answer_block_without_sources(self):
        resp = RAGResponse(answer="Solo respuesta")
        block = format_answer_block(resp)
        assert "Solo respuesta" in block
        assert "Fuentes utilizadas" not in block


# --------------------------------------------------------------------------- #
# Formatters — UI states
# --------------------------------------------------------------------------- #


class TestFormatNoAnswer:
    def test_with_reason(self):
        resp = RAGResponse(
            answer="",
            sources=[],
            grounded=False,
            no_answer_reason="sin datos relevantes",
        )
        msg = format_no_answer(resp)
        assert "información suficiente" in msg
        assert "sin datos relevantes" in msg
        assert "no improvise" in msg.lower() or "improvisar" in msg

    def test_without_reason(self):
        resp = RAGResponse(answer="", sources=[], grounded=False)
        assert "información suficiente" in format_no_answer(resp)


class TestFormatError:
    def test_connection_error(self):
        msg = format_error("connection")
        assert "conectar" in msg
        assert "error técnico" not in msg

    def test_unknown_error_is_friendly(self):
        msg = format_error("unknown")
        assert "error técnico" in msg

    def test_no_internal_details(self):
        exc = RuntimeError("Internal error with API key abc123")
        msg = format_error_message(exc)
        assert "abc123" not in msg
        assert "RuntimeError" not in msg

    def test_connection_error_maps_from_exception(self):
        msg = format_error_message(ConnectionError("refused"))
        assert "conectar" in msg


class TestFormatFileError:
    def test_wrong_type(self):
        assert "No puedo aceptar «notes.exe»" in format_file_error("notes.exe", "type")

    def test_too_big(self):
        assert "50 MB" in format_file_error("gran.pdf", "size")

    def test_empty_file(self):
        assert "vacío" in format_file_error("vacio.pdf", "empty")

    def test_unknown_reason_falls_back_to_read(self):
        assert "No se ha podido leer" in format_file_error("x.pdf", "otra_cosa")


class TestDocumentAndGreetingStates:
    def test_documents_state_counts_files(self):
        msg = format_documents_state(["a.pdf", "b.pdf"])
        assert "2 documentos" in msg
        assert "✓ a.pdf" in msg
        assert "✓ b.pdf" in msg

    def test_documents_state_uses_library_badge(self):
        # 📚 = documentation loaded; 📄 is reserved for sources used (§24).
        assert format_documents_state(["a.pdf"]).startswith("**📚")

    def test_documents_state_singular(self):
        assert "1 documento" in format_documents_state(["a.pdf"])

    def test_documents_state_empty(self):
        msg = format_documents_state([])
        assert "0 documentos" in msg
        assert "(sin archivos)" in msg

    def test_documents_state_removes_duplicates(self):
        msg = format_documents_state(["a.pdf", "a.pdf"])
        assert "1 documento" in msg

    def test_no_documents_state(self):
        msg = format_no_documents()
        assert "no hay documentación" in msg.lower()
        assert "Cargar documentación" in msg

    def test_empty_question(self):
        assert "Escribe una pregunta" in format_empty_question()

    def test_question_too_long_mentions_limit(self):
        assert "800" in format_question_too_long(800)


class TestFormatClarify:
    def test_headline_is_the_expected_prompt(self):
        msg = format_clarify()
        assert "**Claro. Puedo ayudarte a consultar la documentación disponible.**" in msg
        assert "**¿Qué te interesa?**" in msg

    def test_without_documents_invites_upload(self):
        msg = format_clarify()
        assert "Carga tu documentación" in msg
        assert "PDF, TXT y Markdown" in msg

    def test_with_documents_is_contextual(self):
        msg = format_clarify(has_docs=True)
        assert "documentación cargada" in msg
        assert "Carga tu documentación" not in msg

    def test_mid_conversation_prioritizes_the_chat(self):
        msg = format_clarify(in_conversation=True)
        assert "Sigue preguntando" in msg

    def test_docs_and_chat_both_present(self):
        msg = format_clarify(has_docs=True, in_conversation=True)
        assert "documentación cargada" in msg
        assert "Sigue preguntando" in msg

    def test_never_promise_corpus_content(self):
        # The suggestions are orientation, not a claim about the corpus.
        msg = format_clarify(has_docs=True, in_conversation=True)
        for forbidden in ("contiene", "tengo información sobre", "incluye"):
            assert forbidden not in msg


class TestFormatWelcome:
    def test_welcome_identity_and_steps(self):
        msg = format_welcome(is_mock=False)
        assert "Asesor Fiscal IA" in msg
        for word in ("Carga", "Pregunta", "fuentes", "📎"):
            assert word in msg

    def test_welcome_shows_mock_badge(self):
        assert "Modo demostración" in format_welcome(is_mock=True)

    def test_welcome_hides_mock_badge_in_real_mode(self):
        assert "Modo demostración" not in format_welcome(is_mock=False)

    def test_welcome_has_cta_and_compact_steps(self):
        msg = format_welcome(is_mock=False)
        assert "Cargar documentación" in msg
        assert "1️⃣" in msg and "3️⃣" in msg
        assert "**Cómo funciona**" in msg


# --------------------------------------------------------------------------- #
# Mock
# --------------------------------------------------------------------------- #


class TestMockRAG:
    @pytest.mark.asyncio
    async def test_answer_with_two_sources(self):
        mock = MockRAG()
        resp = await mock.ask("¿Qué gastos son deducibles de IVA?", [])
        assert resp.grounded is True
        assert len(resp.sources) == 2
        assert resp.sources[0].page == 42
        assert resp.sources[1].page == 18

    @pytest.mark.asyncio
    async def test_answer_with_three_sources(self):
        mock = MockRAG()
        resp = await mock.ask("¿Cuándo se presenta el modelo 303?", [])
        assert resp.grounded is True
        assert len(resp.sources) == 3
        documents = {s.document for s in resp.sources}
        assert len(documents) == 3

    @pytest.mark.asyncio
    async def test_answer_with_single_source(self):
        mock = MockRAG()
        resp = await mock.ask("¿Cómo me doy de alta como autónomo?", [])
        assert resp.grounded is True
        assert len(resp.sources) == 1

    @pytest.mark.asyncio
    async def test_no_sufficient_information(self):
        mock = MockRAG()
        resp = await mock.ask("¿Qué es el bitcoin?", [])
        assert resp.grounded is False
        assert resp.sources == []
        assert resp.no_answer_reason is not None

    @pytest.mark.asyncio
    async def test_backend_error(self):
        mock = MockRAG()
        with pytest.raises(RuntimeError):
            await mock.ask("¿Hay algún error?", [])

    @pytest.mark.asyncio
    async def test_sources_with_incomplete_metadata(self):
        mock = MockRAG()
        resp = await mock.ask("metadata incompleta", [])
        assert resp.grounded is True
        assert len(resp.sources) == 3
        # Third source has fully missing metadata
        assert resp.sources[2].page is None
        assert resp.sources[2].section is None
        assert resp.sources[2].score is None

    @pytest.mark.asyncio
    async def test_generic_fallback_answer(self):
        mock = MockRAG()
        resp = await mock.ask("pregunta sin escenario", [])
        assert resp.grounded is True
        assert len(resp.sources) == 1

    @pytest.mark.asyncio
    async def test_mock_never_simulates_scores(self):
        # The demo must not invent relevance: only the real backend shows it.
        mock = MockRAG()
        for question in (
            "¿Qué gastos son deducibles de IVA?",
            "¿Cuándo se presenta el modelo 303?",
            "¿Cómo me doy de alta como autónomo?",
            "metadata incompleta",
            "pregunta sin escenario",
        ):
            resp = await mock.ask(question, [])
            assert all(s.score is None for s in resp.sources), question
            # No «relevancia» in any rendered header (snippet text is content).
            assert all(
                "relevancia" not in format_source_header(s) for s in resp.sources
            ), question

    @pytest.mark.asyncio
    async def test_mock_responses_are_immediate(self):
        # No artificial delays: the processing state must only reflect real
        # work (the mock used to sleep 400-900 ms on purpose).
        import time

        mock = MockRAG()
        start = time.monotonic()
        resp = await mock.ask("¿Qué gastos son deducibles de IVA?", [])
        elapsed = time.monotonic() - start
        assert resp.latency_ms is None
        assert elapsed < 0.4

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        ("question", "keyword"),
        [
            ("¿Cómo doy de alta de autónomo?", "036"),
            ("Explícame el IVA", "IVA"),
            ("¿Qué es el modelo 303?", "303"),
            ("¿Qué es el IRPF?", "IRPF"),
            ("¿Qué gastos son deducibles en el IRPF?", "deducibles"),
            ("¿Qué obligaciones fiscales tengo como autónomo?", "obligaciones"),
            ("ayuda", "Puedo ayudarte"),
        ],
    )
    async def test_topic_scenarios_answer_coherently(self, question, keyword):
        # Regression: conversational/valid topics must get a structured,
        # topic-coherent answer instead of the same generic fallback.
        resp = await MockRAG().ask(question, [])
        assert resp.grounded is True
        assert keyword.lower() in resp.answer.lower(), question

    @pytest.mark.asyncio
    async def test_mock_answers_are_identified_as_demo(self):
        # Regression: product-realistic structure, but always marked DEMO.
        for question in (
            "Explícame el IVA",
            "¿Qué es el IRPF?",
            "pregunta sin escenario",
        ):
            resp = await MockRAG().ask(question, [])
            assert "Demo" in resp.answer, question
            assert "demostración" in resp.answer, question

    @pytest.mark.asyncio
    async def test_all_topic_scenarios_bind_sources_to_session(self):
        # Regression: never cite a file the user has not uploaded.
        mock = MockRAG()
        for question in (
            "¿Qué gastos son deducibles de IVA?",
            "¿Cuándo se presenta el modelo 303?",
            "¿Cómo me doy de alta como autónomo?",
            "¿Qué es el IRPF?",
            "¿Qué gastos son deducibles en el IRPF?",
            "¿Qué obligaciones fiscales tengo?",
            "pregunta sin escenario",
        ):
            resp = await mock.ask(
                question, [r"ui\.files\u1\doc.pdf"], labels=["doc-real.pdf"]
            )
            assert all(s.document == "doc-real.pdf" for s in resp.sources), question

    @pytest.mark.asyncio
    async def test_help_scenario_has_no_simulated_sources(self):
        # The orientation fallback must not fabricate evidence.
        resp = await MockRAG().ask("ayuda", [], labels=["doc-real.pdf"])
        assert resp.sources == []

    @pytest.mark.asyncio
    async def test_is_deterministic(self):
        mock = MockRAG()
        first = await mock.ask("¿Qué es el IRPF?", [])
        second = await mock.ask("¿Qué es el IRPF?", [])
        assert first.answer == second.answer
        assert len(first.sources) == len(second.sources)

    @pytest.mark.asyncio
    async def test_sources_bound_to_uploaded_documents(self):
        # Demo rule: simulated sources must cite documents the user loaded.
        mock = MockRAG()
        resp = await mock.ask(
            "¿Qué gastos son deducibles de IVA?",
            [r"ui\.files\u1\u2.pdf"],
            labels=["mi-informe.pdf"],
        )
        assert {s.document for s in resp.sources} == {"mi-informe.pdf"}
        # Simulated content (pages/sections) is preserved.
        assert resp.sources[0].page == 42

    @pytest.mark.asyncio
    async def test_preferred_names_kept_when_uploaded(self):
        mock = MockRAG()
        labels = [
            "manual-practico-iva-2025.pdf",
            "BOE-A-1992-28740-consolidado-37-1992.pdf",
        ]
        resp = await mock.ask("¿Qué gastos son deducibles de IVA?", [], labels=labels)
        assert resp.sources[0].document == "manual-practico-iva-2025.pdf"
        assert resp.sources[1].document.startswith("BOE")


# --------------------------------------------------------------------------- #
# Adapter
# --------------------------------------------------------------------------- #


class TestRagAdapter:
    def test_format_response_with_dict(self):
        adapter = RagAdapter()
        data = {
            "answer": "Test answer",
            "sources": [{"document": "Doc.pdf", "content": "content", "page": 5}],
            "grounded": True,
        }
        resp = adapter.format_response(data)
        assert isinstance(resp, RAGResponse)
        assert resp.answer == "Test answer"
        assert len(resp.sources) == 1

    def test_format_response_with_rag_response(self):
        adapter = RagAdapter()
        resp1 = RAGResponse(answer="test")
        resp2 = adapter.format_response(resp1)
        assert resp2 is resp1

    def test_format_response_with_string(self):
        adapter = RagAdapter()
        resp = adapter.format_response("plain text")
        assert resp.answer == "plain text"
        assert resp.grounded is False

    @pytest.mark.asyncio
    async def test_adapter_ask_uses_mock(self):
        adapter = RagAdapter()
        resp = await adapter.ask("¿IVA deducible?", [])
        assert isinstance(resp, RAGResponse)
        assert resp.grounded is True

    @pytest.mark.asyncio
    async def test_adapter_forwards_labels_to_mock(self):
        adapter = RagAdapter(backend=None)
        resp = await adapter.ask(
            "¿Qué gastos son deducibles de IVA?", [], labels=["mio.pdf"]
        )
        assert all(s.document == "mio.pdf" for s in resp.sources)

    def test_adapter_is_mock_by_default(self):
        assert RagAdapter().is_mock is True
