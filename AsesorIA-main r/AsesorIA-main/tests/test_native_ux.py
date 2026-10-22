"""Phase 1 + Phase 2 native UX coverage (starter categories, micro-decisions,
side-panel sources, charts, mock starter scenarios and asset contracts).

New file only — existing tests are never touched (zero-regression rule).
"""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from ui import app
from ui.contracts import RAGResponse, Source
from ui.mock_rag import MockRAG

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def cl_thread():
    """Minimal Chainlit context so Element construction (thread_id default)
    works outside a live session. Elements are only built, never sent."""
    ctx_mod = sys.modules["chainlit.context"]
    token = ctx_mod.context_var.set(
        SimpleNamespace(session=SimpleNamespace(thread_id="test-thread"))
    )
    yield
    ctx_mod.context_var.reset(token)

# Exact order of ui/app.py STARTER_CATEGORIES (mirrored by public/custom.js).
NINE_QUESTIONS = [
    "¿Qué IRPF debo aplicar en mis facturas?",
    "¿Qué gastos son realmente deducibles en Hacienda?",
    "¿Cómo presento los trimestres?",
    "¿Cómo funciona la Tarifa Plana?",
    "¿Qué es la regularización anual por ingresos reales?",
    "¿Cómo cambio mi base de cotización?",
    "¿Cuándo hay que darse de alta como autónomo?",
    "¿Puedo ser autónomo y tener empleo por cuenta ajena?",
    "¿Qué pasa si me doy de baja médica o cese de actividad?",
]


class TestStarterCategories:
    def test_three_categories_nine_questions(self):
        assert len(app.STARTER_CATEGORIES) == 3
        flat = []
        for icon, label, questions in app.STARTER_CATEGORIES:
            assert icon.strip()
            assert label.strip()
            assert len(questions) == 3
            for button, question in questions:
                assert button.strip()
                assert question.startswith("¿")
                flat.append(question)
        assert flat == NINE_QUESTIONS

    def test_callback_is_registered_coroutine(self):
        assert asyncio.iscoroutinefunction(app.starter_categories)


class TestDecisionMatcher:
    @pytest.mark.parametrize(
        "question,expected",
        [
            ("¿Cómo presento los trimestres?", "trimestres"),
            ("¿Qué trimestre debo declarar?", "trimestres"),
            ("¿Qué trimestres formularios debo presentar?", "trimestres"),
            ("¿Qué estimación debo elegir?", "estimacion"),
            ("¿Qué tipo de estimación me conviene?", "estimacion"),
            ("¿Cuándo se presenta el modelo 303?", None),
            ("¿Qué es el IVA soportado y cómo se deduce?", None),
            ("¿Qué obligaciones fiscales tengo como autónomo?", None),
            ("¿Cómo cambio mi base de cotización?", None),
            ("hola", None),
            ("", None),
        ],
    )
    def test_kind_matching(self, question, expected):
        assert app._decision_kind(question) == expected

    def test_starters_never_all_trigger(self):
        # Only the trimestres starter may open the button flow.
        kinds = [app._decision_kind(q) for q in NINE_QUESTIONS]
        assert kinds.count("trimestres") == 1
        assert kinds.count("estimacion") == 0


class TestAskDecisionFallback:
    @pytest.mark.asyncio
    async def test_returns_none_outside_session(self):
        # No Chainlit session → AskActionMessage fails → graceful None,
        # the caller then answers normally (decision layer never blocks).
        assert await app._ask_decision("trimestres") is None
        assert await app._ask_decision("estimacion") is None


class TestSourceElements:
    pytestmark = pytest.mark.usefixtures("cl_thread")

    def test_side_display_and_label(self):
        src = Source(document="doc.pdf", content="fragmento", page=3, section="S")
        resp = RAGResponse(answer="ok", sources=[src], grounded=True)
        elements = app._source_elements(resp)
        assert len(elements) == 1
        el = elements[0]
        assert el.display == "side"
        assert el.language is None  # plain text: no bogus «es» code chip
        assert el.name.startswith("Fuente 1: ")
        assert el.name.endswith("doc.pdf")
        assert "**" not in el.content  # no raw markdown markers

    def test_empty_source_list_yields_nothing(self):
        assert app._source_elements(RAGResponse(answer="x")) == []

    def test_blank_source_is_skipped(self):
        src = Source(document="", content="")
        resp = RAGResponse(answer="ok", sources=[src], grounded=True)
        assert app._source_elements(resp) == []


class TestChartElement:
    pytestmark = pytest.mark.usefixtures("cl_thread")

    def test_valid_chart_renders_plotly(self):
        resp = RAGResponse(
            answer="x",
            chart={
                "title": "IVA",
                "labels": ["Devengado", "Soportado"],
                "values": [100.0, 40.0],
                "y_label": "€",
            },
        )
        el = app._chart_element(resp)
        assert el is not None
        assert el.display == "inline"

    @pytest.mark.parametrize(
        "chart",
        [
            None,
            "not-a-dict",
            {"labels": ["A"], "values": [1, 2]},
            {"labels": [], "values": []},
            {"labels": ["A"], "values": []},
        ],
    )
    def test_bad_or_missing_chart_is_skipped(self, chart):
        resp = RAGResponse(answer="x")
        resp.chart = chart
        assert app._chart_element(resp) is None


class TestChartContract:
    def test_chart_defaults_to_none(self):
        assert RAGResponse(answer="x").chart is None

    def test_from_dict_roundtrip(self):
        payload = {
            "answer": "x",
            "grounded": True,
            "sources": [],
            "chart": {"labels": ["T1"], "values": [10]},
        }
        resp = RAGResponse.from_dict(payload)
        assert resp.chart == {"labels": ["T1"], "values": [10]}

    def test_from_any_reads_chart_attribute(self):
        class Obj:
            answer = "x"
            chart = {"labels": ["T1"], "values": [10]}

        resp = RAGResponse.from_any(Obj())
        assert resp.chart is not None
        assert resp.chart["values"] == [10]

    def test_legacy_payload_without_chart(self):
        resp = RAGResponse.from_dict({"answer": "x", "grounded": True})
        assert resp.chart is None


class TestMockStarterScenarios:
    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "question,needle",
        [
            (NINE_QUESTIONS[0], "retención"),       # IRPF en facturas
            (NINE_QUESTIONS[2], "303"),             # trimestres
            (NINE_QUESTIONS[3], "Tarifa Plana"),    # tarifa plana
            (NINE_QUESTIONS[4], "regulariza"),      # regularización
            (NINE_QUESTIONS[5], "base de cotización"),
            (NINE_QUESTIONS[7], "compatib"),        # cuenta ajena
            (NINE_QUESTIONS[8], "cese"),            # baja / cese
        ],
    )
    async def test_starter_question_hits_scenario(self, question, needle):
        resp = await MockRAG().ask(question, [])
        assert resp.grounded
        assert resp.has_answer
        assert needle.lower() in resp.answer.lower()

    @pytest.mark.asyncio
    async def test_grounding_starter_keeps_existing_scenario(self):
        resp = await MockRAG().ask(NINE_QUESTIONS[1], [])
        assert resp.grounded
        assert resp.sources

    @pytest.mark.asyncio
    async def test_high_starter_keeps_existing_scenario(self):
        resp = await MockRAG().ask(NINE_QUESTIONS[6], [])
        assert resp.grounded
        assert resp.sources

    @pytest.mark.asyncio
    async def test_iva_scenario_ships_chart(self):
        resp = await MockRAG().ask("¿Qué es el IVA?", [])
        assert resp.chart is not None
        assert len(resp.chart["labels"]) == len(resp.chart["values"]) == 3

    @pytest.mark.asyncio
    async def test_gastos_scenario_has_no_chart(self):
        resp = await MockRAG().ask(NINE_QUESTIONS[1], [])
        assert resp.chart is None

    @pytest.mark.asyncio
    async def test_model_303_dates_scenario_untouched(self):
        # Smoke-test question must keep its original behaviour.
        resp = await MockRAG().ask("¿Cuándo se presenta el modelo 303?", [])
        assert resp.grounded
        assert resp.sources


class TestAssetContracts:
    def test_theme_is_warm_sand_green(self):
        theme = json.loads(
            (ROOT / "ui" / "public" / "theme.json").read_text(encoding="utf-8")
        )
        light = theme["variables"]["light"]
        dark = theme["variables"]["dark"]
        assert light["--background"].startswith("40 35%")   # warm sand
        assert light["--primary"].startswith("152 45%")      # forest green
        assert dark["--background"].startswith("150 12%")
        assert dark["--primary"].startswith("152 45%")

    def test_css_is_namespaced(self):
        css = (ROOT / "ui" / "public" / "custom.css").read_text(encoding="utf-8")
        assert ".-ias-card" in css
        assert ".-ias-fab" in css
        assert ".-ias-panel" in css
        # blue fallbacks were replaced by the green palette
        assert "221 83% 54%" not in css

    def test_custom_js_is_defensive(self):
        js = (ROOT / "ui" / "public" / "custom.js").read_text(encoding="utf-8")
        assert "MutationObserver" in js
        assert "getElementById(WELCOME_ID)" in js
        assert "getElementById(FAB_ID)" in js
        assert '"-ias-fab"' in js
        # native-dispatch path (setter + input + Enter)
        assert "HTMLTextAreaElement" in js
        assert '"Enter"' in js

    def test_nine_questions_mirrored_in_js(self):
        js = (ROOT / "ui" / "public" / "custom.js").read_text(encoding="utf-8")
        for question in NINE_QUESTIONS:
            assert question in js

    def test_plotly_declared_in_requirements(self):
        req = (ROOT / "requirements.txt").read_text(encoding="utf-8")
        assert "plotly" in req.lower()

    def test_ux_architecture_doc_exists(self):
        doc = ROOT / "docs" / "ux-ui-architecture.md"
        assert doc.exists()
        text = doc.read_text(encoding="utf-8")
        assert "set_starter_categories" in text
        assert "display=\"side\"" in text or "display=`side`" in text or "display=\\\"side\\\"" in text or "display=\"side\"" in text
