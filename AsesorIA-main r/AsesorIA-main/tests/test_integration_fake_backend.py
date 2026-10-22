"""Integration tests: UI adapter against fake backends.

Two layers:

A. Contract cases (theoretical shape): what ``src/rag/engine.py`` may
   return once the RAG team connects it (7 contract cases + tolerance
   variants) — proves that ``RagAdapter`` and the formatters consume any
   accepted response without losing traceability.

B. Real backend shape (pre-integration): exactly what exists today,
   verified read-only against ``RAGPipeline.answer_query`` (main) and the
   retriever of PRs #25-#28:

       answer_query(question) -> {"answer": str,
                                  "source_documents": [Document]}

   with LangChain-style documents (``page_content`` + retrieval metadata),
   NO "sources" key, NO "grounded"/"score"/"latency_ms".

Scope: frontend only (adapter, contract, formatters). No retrieval, no
embeddings, no vector store.
"""

import pytest

from ui.contracts import RAGResponse, Source
from ui.formatters import (
    format_answer_block,
    format_error,
    format_no_answer,
    format_source_header,
    format_sources_block,
)
from ui.rag_adapter import RagAdapter


class FakeBackend:
    """Test backend: returns the configured result or raises the given error."""

    def __init__(self, result=None, error=None):
        self.result = result
        self.error = error
        self.calls = []

    def _respond(self, question, documents):
        self.calls.append((question, documents))
        if self.error is not None:
            raise self.error
        return self.result

    async def query(self, question, documents):
        return self._respond(question, documents)


class FakeBackendSync:
    """Sync backend exposing only `ask()` (must also be accepted)."""

    def __init__(self, result):
        self.result = result

    def ask(self, question, documents):
        return self.result


CONTRACT_RESPONSE = {
    "answer": "Los gastos de suministros son deducibles si están afectos a la actividad.",
    "sources": [
        {
            "document": "Manual_Renta.pdf",
            "page": 42,
            "section": "Gastos deducibles",
            "content": "Son deducibles los gastos de suministros del local…",
            "score": 0.94,
        },
        {
            "document": "BOE-consolidado.pdf",
            "page": 18,
            "section": "Artículo 30.2",
            "content": "Serán deducibles las cantidades que correspondan…",
            "score": 0.87,
        },
    ],
    "grounded": True,
    "no_answer_reason": None,
    "latency_ms": 320.0,
}


# --------------------------------------------------------------------------- #
# 1-2-3-7. Contract cases with a simulated backend
# --------------------------------------------------------------------------- #


class TestFakeBackendContractCases:
    @pytest.mark.asyncio
    async def test_case1_answer_with_two_full_sources(self):
        adapter = RagAdapter(backend=FakeBackend(CONTRACT_RESPONSE))
        resp = await adapter.ask("¿Qué gastos son deducibles?", ["Manual_Renta.pdf"])

        assert isinstance(resp, RAGResponse)
        assert resp.grounded is True
        assert len(resp.sources) == 2
        assert resp.latency_ms == 320.0

        # The UI shows full traceability after the answer.
        block = format_answer_block(resp)
        assert "Fuentes utilizadas · 2" in block
        assert "**1. Manual_Renta.pdf**" in block
        assert "pág. 42" in block
        assert "Gastos deducibles" in block
        assert "relevancia 0,94" in block
        assert "> \"Son deducibles los gastos" in block

    @pytest.mark.asyncio
    async def test_case2_answer_with_one_source(self):
        adapter = RagAdapter(backend=FakeBackend({**CONTRACT_RESPONSE, "sources": CONTRACT_RESPONSE["sources"][:1]}))
        resp = await adapter.ask("¿Y el IVA?", ["Manual_Renta.pdf"])

        assert len(resp.sources) == 1
        block = format_answer_block(resp)
        assert "Fuentes utilizadas · 1" in block

    @pytest.mark.asyncio
    async def test_case3_answer_without_sources(self):
        payload = {
            "answer": "Respuesta sin procedencia verificable.",
            "sources": [],
            "grounded": True,
        }
        adapter = RagAdapter(backend=FakeBackend(payload))
        resp = await adapter.ask("Pregunta", [])

        assert resp.has_answer is True
        assert resp.has_sources is False
        # No block is emitted without sources (the UI must not break).
        assert format_sources_block(resp.sources) == ""
        assert "Fuentes utilizadas" not in format_answer_block(resp)

    @pytest.mark.asyncio
    async def test_case4_groundless_answer(self):
        payload = {
            "answer": "",
            "sources": [],
            "grounded": False,
            "no_answer_reason": "sin resultados relevantes en la documentación",
        }
        adapter = RagAdapter(backend=FakeBackend(payload))
        resp = await adapter.ask("Criptomonedas", [])

        assert resp.grounded is False
        assert resp.has_answer is False
        # The UI distinguishes "no information" from an error.
        text = format_no_answer(resp)
        assert "No he encontrado" in text
        assert "error" not in text.lower()

    @pytest.mark.asyncio
    async def test_case5_incomplete_metadata(self):
        payload = {
            "answer": "Respuesta con metadatos parciales.",
            "sources": [{"document": "parcial.pdf", "content": "Fragmento…"}],
            "grounded": True,
        }
        adapter = RagAdapter(backend=FakeBackend(payload))
        resp = await adapter.ask("Pregunta", [])

        source = resp.sources[0]
        assert source.page is None
        assert source.section is None
        assert source.score is None

        header = format_source_header(source, index=1)
        # Missing fields are omitted, never padded with placeholder text.
        assert "**1. parcial.pdf**" in header
        assert "no disponible" not in header
        assert "None" not in header
        assert "relevancia" not in header

    @pytest.mark.asyncio
    async def test_case6_backend_error_propagates(self):
        backend = FakeBackend(error=RuntimeError("chroma caído"))
        adapter = RagAdapter(backend=backend)

        with pytest.raises(RuntimeError):
            await adapter.ask("Pregunta", [])

        # The UI catches the exception and shows friendly copy (no stack trace).
        assert "error técnico" in format_error("unknown")

    @pytest.mark.asyncio
    async def test_case7_latency_available(self):
        adapter = RagAdapter(backend=FakeBackend(CONTRACT_RESPONSE))
        resp = await adapter.ask("Pregunta", [])
        assert resp.latency_ms == pytest.approx(320.0)


# --------------------------------------------------------------------------- #
# Adapter tolerance (never raise on optional metadata)
# --------------------------------------------------------------------------- #


class TestAdapterTolerance:
    @pytest.mark.asyncio
    async def test_passes_question_and_documents_to_backend(self):
        backend = FakeBackend(CONTRACT_RESPONSE)
        adapter = RagAdapter(backend=backend)
        await adapter.ask("¿IVA?", ["a.pdf", "b.pdf"])
        assert backend.calls == [("¿IVA?", ["a.pdf", "b.pdf"])]

    def test_is_mock_false_with_backend(self):
        assert RagAdapter(backend=FakeBackend({})).is_mock is False
        assert RagAdapter().is_mock is True

    @pytest.mark.asyncio
    async def test_sources_none(self):
        adapter = RagAdapter(backend=FakeBackend({"answer": "ok", "sources": None}))
        resp = await adapter.ask("P", [])
        assert resp.sources == []

    @pytest.mark.asyncio
    async def test_sources_single_object_instead_of_list(self):
        single = {"document": "unico.pdf", "content": "Fragmento"}
        adapter = RagAdapter(backend=FakeBackend({"answer": "ok", "sources": single}))
        resp = await adapter.ask("P", [])
        assert len(resp.sources) == 1
        assert resp.sources[0].document == "unico.pdf"

    @pytest.mark.asyncio
    async def test_string_typed_page_and_score(self):
        payload = {
            "answer": "ok",
            "sources": [
                {"document": "d.pdf", "content": "c", "page": "42", "score": "0.94"}
            ],
        }
        adapter = RagAdapter(backend=FakeBackend(payload))
        resp = await adapter.ask("P", [])
        assert resp.sources[0].page == 42
        assert resp.sources[0].score == pytest.approx(0.94)

    @pytest.mark.asyncio
    async def test_document_as_path_is_shown_as_filename(self):
        payload = {
            "answer": "ok",
            "sources": [
                {"document": "C:\\datos\\docs\\Manual_Renta_2025.pdf", "content": "c"}
            ],
        }
        adapter = RagAdapter(backend=FakeBackend(payload))
        resp = await adapter.ask("P", [])
        assert resp.sources[0].document == "Manual_Renta_2025.pdf"

    @pytest.mark.asyncio
    async def test_langchain_like_object(self):
        class Document:
            page_content = "Fragmento recuperado"
            metadata = {"source": "carpeta/modelo-303.pdf", "page": 7, "heading": "Modelo"}
            score = 0.8

        adapter = RagAdapter(backend=FakeBackend({"answer": "ok", "sources": [Document()]}))
        resp = await adapter.ask("P", [])

        source = resp.sources[0]
        assert source.content == "Fragmento recuperado"
        assert source.document == "modelo-303.pdf"
        assert source.page == 7
        assert source.section == "Modelo"
        assert source.score == pytest.approx(0.8)

    @pytest.mark.asyncio
    async def test_metadata_only_fields_are_recovered(self):
        payload = {
            "answer": "ok",
            "sources": [
                {"content": "c", "metadata": {"source": "doc.pdf", "page": 3}}
            ],
        }
        adapter = RagAdapter(backend=FakeBackend(payload))
        resp = await adapter.ask("P", [])
        assert resp.sources[0].document == "doc.pdf"
        assert resp.sources[0].page == 3

    @pytest.mark.asyncio
    async def test_answer_none_and_grounded_string(self):
        adapter = RagAdapter(
            backend=FakeBackend({"answer": None, "grounded": "false", "sources": []})
        )
        resp = await adapter.ask("P", [])
        assert resp.answer == ""
        assert resp.grounded is False

    @pytest.mark.asyncio
    async def test_none_response_is_not_the_text_none(self):
        adapter = RagAdapter(backend=FakeBackend(None))
        resp = await adapter.ask("P", [])
        assert resp.answer == ""
        assert resp.grounded is False
        assert resp.has_answer is False

    @pytest.mark.asyncio
    async def test_response_object_passthrough(self):
        original = RAGResponse(answer="ok", sources=[], grounded=True)
        adapter = RagAdapter(backend=FakeBackend(original))
        resp = await adapter.ask("P", [])
        assert resp is original

    @pytest.mark.asyncio
    async def test_sync_backend_with_ask_only(self):
        adapter = RagAdapter(backend=FakeBackendSync(CONTRACT_RESPONSE))
        resp = await adapter.ask("P", [])
        assert isinstance(resp, RAGResponse)
        assert resp.has_sources

    @pytest.mark.asyncio
    async def test_backend_without_query_nor_ask_raises_clear_error(self):
        adapter = RagAdapter(backend=object())
        with pytest.raises(TypeError):
            await adapter.ask("P", [])

    @pytest.mark.asyncio
    async def test_default_adapter_uses_mock(self):
        adapter = RagAdapter()
        assert adapter.is_mock is True
        resp = await adapter.ask("IVA deducible?", [])
        assert resp.has_answer is True
        assert isinstance(resp.sources[0], Source)


# --------------------------------------------------------------------------- #
# B. Real backend shape (pre-integration): answer_query -> source_documents
# --------------------------------------------------------------------------- #


class FakeDocument:
    """Duck-typed langchain_core.documents.Document (page_content+metadata).

    UI tests never import backend packages: the shape is what matters.
    """

    def __init__(self, page_content: str, metadata: dict):
        self.page_content = page_content
        self.metadata = metadata


def _real_metadata(**overrides) -> dict:
    """Metadata exactly as the real retriever returns it (PRs #25-#28)."""
    metadata = {
        "doc_id": "manual-practico-iva-2025",
        "tax": "IVA",
        "doc_type": "manual",
        "fiscal_year": 2025,
        "section_label": "Deducción del IVA soportado",
        "section_path": "IVA > Deducción > Soportado",
        "page": 42,
        "page_end": 43,
        "source_url": "corpus/manual-practico-iva-2025.pdf",
        "retrieved_at": "2026-10-05T09:00:00+00:00",
        "source_scope": "public",
        "chunk_index": 17,
    }
    metadata.update(overrides)
    # The retriever guarantees this integration alias on every Document.
    metadata.setdefault(
        "source", metadata.get("source_url") or metadata.get("doc_id")
    )
    return metadata


class FakePipelineBackend:
    """The REAL backend surface: ``answer_query(question) -> dict``.

    Returns ``{"answer": str, "source_documents": [FakeDocument]}`` — no
    "sources", "grounded", "score" or "latency_ms" keys.
    """

    def __init__(
        self,
        source_documents=None,
        answer: str = "Respuesta del pipeline.",
        error: BaseException | None = None,
    ):
        self.source_documents = list(source_documents or [])
        self.answer = answer
        self.error = error
        self.calls: list[str] = []

    def answer_query(self, question: str) -> dict:
        self.calls.append(question)
        if self.error is not None:
            raise self.error
        return {"answer": self.answer, "source_documents": self.source_documents}


class TestRealBackendShape:
    """§10/§11: the frontend against the contract really observed."""

    @pytest.mark.asyncio
    async def test_single_source_mapping(self):
        backend = FakePipelineBackend(
            [FakeDocument("El IVA soportado es deducible cuando…", _real_metadata())]
        )
        resp = await RagAdapter(backend=backend).ask("¿Qué es deducible?", ["x.pdf"])

        # Signature introspection: answer_query takes only the question.
        assert backend.calls == ["¿Qué es deducible?"]
        assert resp.grounded is True  # default: the backend does not send it yet
        assert len(resp.sources) == 1
        src = resp.sources[0]
        assert src.document == "manual-practico-iva-2025.pdf"  # alias, basename
        assert src.content.startswith("El IVA soportado")
        assert src.page == 42
        assert src.section == "Deducción del IVA soportado"  # from section_label
        assert src.score is None  # the real retriever emits no score
        # Full retrieval metadata is never lost (page_end, doc_id, …).
        assert src.metadata["doc_id"] == "manual-practico-iva-2025"
        assert src.metadata["page_end"] == 43
        assert src.metadata["chunk_index"] == 17

        block = format_answer_block(resp)
        assert "relevancia" not in block  # never invented by the frontend
        assert "> \"El IVA soportado es deducible" in block

    @pytest.mark.asyncio
    async def test_multiple_sources(self):
        docs = [
            FakeDocument(
                f"Fragmento {i}",
                _real_metadata(page=i, doc_id=f"doc{i}", source=f"docs/doc{i}.pdf"),
            )
            for i in (1, 2, 3)
        ]
        backend = FakePipelineBackend(docs, answer="Respuesta con tres fuentes.")
        resp = await RagAdapter(backend=backend).ask("P", [])

        assert len(resp.sources) == 3
        block = format_sources_block(resp.sources)
        assert "Fuentes utilizadas · 3" in block
        assert "**1. doc1.pdf**" in block
        assert "**3. doc3.pdf**" in block

    @pytest.mark.asyncio
    async def test_section_falls_back_to_section_path(self):
        backend = FakePipelineBackend(
            [FakeDocument("Frag", _real_metadata(section_label=None))]
        )
        resp = await RagAdapter(backend=backend).ask("P", [])
        assert resp.sources[0].section == "IVA > Deducción > Soportado"

    @pytest.mark.asyncio
    async def test_incomplete_metadata_degrades_cleanly(self):
        backend = FakePipelineBackend([FakeDocument("Frag mínima", {"source": "unica.pdf"})])
        resp = await RagAdapter(backend=backend).ask("P", [])

        src = resp.sources[0]
        assert src.document == "unica.pdf"
        assert src.page is None and src.section is None and src.score is None
        # Header shows only what exists: no placeholder padding (§15).
        assert format_source_header(src, index=1) == "**1. unica.pdf**"

    @pytest.mark.asyncio
    async def test_realistic_score_is_shown_when_backend_provides_it(self):
        backend = FakePipelineBackend(
            [FakeDocument("Frag", _real_metadata(score=0.83))]
        )
        resp = await RagAdapter(backend=backend).ask("P", [])

        assert resp.sources[0].score == pytest.approx(0.83)
        assert "relevancia 0,83" in format_source_header(resp.sources[0])

    @pytest.mark.asyncio
    async def test_score_is_never_converted(self):
        # §8: the adapter must not invent distance→similarity conversions —
        # whatever the backend reports is displayed as received.
        backend = FakePipelineBackend(
            [FakeDocument("Frag", _real_metadata(score=0.17))]
        )
        resp = await RagAdapter(backend=backend).ask("P", [])

        assert resp.sources[0].score == pytest.approx(0.17)
        assert "relevancia 0,17" in format_source_header(resp.sources[0])

    @pytest.mark.asyncio
    async def test_empty_source_documents(self):
        backend = FakePipelineBackend(
            [], answer="El pipeline responde aunque no haya documentos."
        )
        resp = await RagAdapter(backend=backend).ask("P", [])

        assert resp.has_answer is True
        assert resp.has_sources is False
        assert format_sources_block(resp.sources) == ""
        # grounded must come from the RAG layer when it exists (§7: the UI
        # does not invent a grounding policy) — default stays permissive.
        assert resp.grounded is True

    @pytest.mark.asyncio
    async def test_no_answer_state_ready_when_backend_signals_it(self):
        backend = FakePipelineBackend()

        def _no_answer(question: str) -> dict:
            backend.calls.append(question)
            return {
                "answer": "",
                "source_documents": [],
                "grounded": False,
                "no_answer_reason": "ningún fragmento supera el umbral",
            }

        backend.answer_query = _no_answer
        resp = await RagAdapter(backend=backend).ask("Criptomonedas", [])

        assert resp.grounded is False
        text = format_no_answer(resp)
        assert "No he encontrado" in text
        assert "error" not in text.lower()

    @pytest.mark.asyncio
    async def test_error_propagates_as_friendly_copy(self):
        backend = FakePipelineBackend(error=RuntimeError("chroma caído"))
        adapter = RagAdapter(backend=backend)
        with pytest.raises(RuntimeError):
            await adapter.ask("P", [])
        assert "error técnico" in format_error("unknown")

    def test_session_id_is_forwarded_to_create_backend(self, monkeypatch):
        import ui.rag_adapter as adapter_module

        captured: dict = {}

        def fake_create_backend(session_id=None):
            captured["session_id"] = session_id
            return FakePipelineBackend()

        monkeypatch.setattr(adapter_module, "create_backend", fake_create_backend)
        adapter = RagAdapter(session_id="sesion-abc123")

        assert captured["session_id"] == "sesion-abc123"
        assert adapter.session_id == "sesion-abc123"
        assert adapter.is_mock is False

    @pytest.mark.asyncio
    async def test_very_long_answer_is_preserved(self):
        long_answer = ("Respuesta extensa basada en documentación. " * 600).strip()
        backend = FakePipelineBackend([], answer=long_answer)
        resp = await RagAdapter(backend=backend).ask("P", [])

        assert resp.answer == long_answer
        assert format_answer_block(resp).startswith(long_answer)
