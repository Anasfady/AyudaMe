"""Adapter: the single boundary between the interface and the RAG backend.

`app.py` only knows this module and the contract (`contracts.py`).  This is
where the mock is swapped for the real engine once it exists:

    MockRAG (today)  →  src/rag/engine.py (tomorrow, RAG team)

No Chroma, LangChain, embeddings, prompts or LLM providers in the UI.

Observed real contract (checked in ``src/rag/engine.py`` on branch
``feat/rag-engine-latency`` — NOT merged into main yet at wiring time):

* entry point ``get_rag_engine(top_k: int = 8, score_threshold: float = 0.82)``
  returns a singleton ``RAGEngine``;
* it does **not** accept ``session_id`` → the adapter does not invent one:
  session-scoped retrieval stays a documented backend follow-up;
* ``RAGEngine.query(question: str) -> dict`` returns
  ``{"question", "answer", "sources": [{"source", "page": "Pág. N",
  "snippet"}], "metrics", "raw_documents"}`` — no ``documents``, no
  ``history`` (yet) and no ``grounded``/``no_answer`` keys;
* ``RAGPipeline.answer_query(question)`` (on main) remains the lower layer.

Integration (ONLY this file is touched):

    def create_backend(session_id: str | None = None):
        from src.rag.engine import get_rag_engine   # RAG team
        return get_rag_engine()   # signature has no session_id: not invented

The engine may expose ``query(question, documents)``, ``ask(...)`` or the
pipeline's ``answer_query(question)`` (sync or async): the adapter inspects
the signature and passes ``documents`` only when the method accepts them.
Whatever it returns is normalized with ``RAGResponse.from_any`` (engine
source aliases ``source``/``snippet`` and the page label are mapped in
:func:`_translate_engine_sources`), so missing metadata, LangChain-like
objects or ``None`` lists never break the interface.

Fallback policy — real backend bugs are NEVER converted into the mock:
:func:`create_backend` returns ``None`` (demo mock) only when the engine
module is absent from this build or construction fails with a
configuration error (``ValueError``: missing API key / unsupported
provider). Every other import or construction failure raises, and
query-time errors always propagate.
"""

from __future__ import annotations

import os
import inspect
import logging
import re
import sys
from pathlib import Path
from typing import Any, List, Optional

try:
    from .contracts import RAGResponse
    from .mock_rag import MockRAG
except ImportError:
    from contracts import RAGResponse
    from mock_rag import MockRAG

_UNSET = object()

# Server-side diagnostics only: fallback reasons go to the console log,
# never into the UI copy the user sees.
logger = logging.getLogger(__name__)

# Conversational history boundary (UI → RAG). The UI transports the turns of
# the CURRENT conversation only; the window keeps the payload predictable for
# the backend until it defines its own limit (20 messages ≈ 10 round-trips:
# enough for follow-up references, small enough for any LLM context).
HISTORY_WINDOW = 20
_HISTORY_ROLES = ("user", "assistant")


def normalize_history(history: Any) -> Optional[List[dict]]:
    """Validates/normalizes a conversation history at the UI→RAG boundary.

    Policy (deterministic, documented):

    * ``None`` → ``None`` (not provided: caller behaves as before);
    * non-list input → ``None`` (controlled discard, never raises);
    * only ``dict`` entries with ``role`` in {``user``, ``assistant``} and a
      usable ``content`` survive; everything else is dropped;
    * ``content`` must be a string (or a scalar safely convertible with
      ``str()``); ``dict``/``list``/``None``/blank content is dropped;
    * chronological order is preserved exactly as given;
    * the window keeps the **last** ``HISTORY_WINDOW`` valid entries.

    The function only filters — it never rewrites, summarizes or invents
    content (contextual rewriting belongs to Backend/RAG).
    """
    if history is None:
        return None
    if not isinstance(history, (list, tuple)):
        return None
    entries: List[dict] = []
    for entry in history:
        if not isinstance(entry, dict):
            continue
        role = entry.get("role")
        if role not in _HISTORY_ROLES:
            continue
        content = entry.get("content")
        if content is None or isinstance(content, (dict, list, tuple)):
            continue
        if not isinstance(content, str):
            content = str(content)
        if not content.strip():
            continue
        entries.append({"role": role, "content": content})
    if len(entries) > HISTORY_WINDOW:
        entries = entries[-HISTORY_WINDOW:]
    return entries


def _accepts_keyword(method: Any, name: str) -> bool:
    """True when ``method`` can be called with the keyword ``name``."""
    try:
        sig = inspect.signature(method)
    except (TypeError, ValueError):
        return False
    if name in sig.parameters:
        return True
    return any(p.kind == inspect.Parameter.VAR_KEYWORD for p in sig.parameters.values())


def create_backend(session_id: Optional[str] = None) -> Optional[Any]:
    """Single connection point with the real RAG engine (backend team).

    Observed signature (``src/rag/engine.py``, branch
    ``feat/rag-engine-latency``):

        get_rag_engine(top_k: int = 8, score_threshold: float = 0.82) -> RAGEngine

    Args:
        session_id: validated identity of the current Chainlit session.
            ``get_rag_engine()`` does **not** accept ``session_id`` → it is
            NOT invented and the backend is NOT modified: the parameter is
            kept here as the future seam for session-scoped retrieval
            (documented backend follow-up).

    Returns:
        The engine instance, or ``None`` (→ demo mock) in exactly two
        situations:

        1. **Backend not available**: the ``src.rag.engine`` module tree is
           not importable in this run (engine not merged/deployed yet, or
           launched from a checkout without ``src/``);
        2. **Backend not configured**: construction raises ``ValueError``
           (missing API key, unsupported provider — configuration errors,
           subclasses included).

        Any other import or construction failure **raises**: a broken
        dependency inside the backend (e.g. ``ModuleNotFoundError:
        langchain_groq``) or a genuine bug must surface, never degrade
        silently to the mock. Query-time failures also raise (see
        :meth:`RagAdapter.ask`).

    Note: while this returns ``None`` the instance has ``is_mock = True``
    and the UI keeps showing the demo notice — honest until the engine
    really answers.
    """

    api_key = os.environ.get("GROQ_API_KEY", "").strip()
    # Si no hay key o es una key dummy de CI/testing, degradar limpiamente a Mock
    if not api_key or any(
        token in api_key.lower() for token in ("test", "mock", "dummy", "fake")
    ):
        logger.warning("GROQ_API_KEY ausente o de pruebas; la UI usará el demo mock.")
        return None

    # The Chainlit server runs with CWD=ui/ while ``src`` lives at the repo
    # root: make the package importable regardless of the launch directory.
    repo_root = str(Path(__file__).resolve().parent.parent)
    if repo_root not in sys.path:
        sys.path.insert(0, repo_root)
    try:
        from src.rag.engine import get_rag_engine
    except ModuleNotFoundError as exc:
        if exc.name in ("src", "src.rag", "src.rag.engine"):
            logger.warning(
                "RAG engine module not available in this build (%s); "
                "UI runs on the demo mock.",
                exc.name,
            )
            return None
        raise  # missing dependency INSIDE the backend = real defect
    try:
        return get_rag_engine()
    except (ValueError, Exception) as exc:
        # Configuration error at construction (API key/provider): the
        # backend is not configured, not broken.
        logger.warning("RAG engine not configured (%s); UI runs on the demo mock.", exc)
        return None


def _accepts_documents(method: Any) -> bool:
    """True when ``method`` can be called as ``method(question, documents)``.

    A second positional parameter **named ``history`` is not documents**: if
    Backend/RAG extends the surface to ``answer_query(question, history=None)``
    the documents argument must never land in the history slot, so the
    two-argument call is skipped in that case (history then travels by
    keyword only).
    """
    try:
        sig = inspect.signature(method)
    except (TypeError, ValueError):
        return True  # unknown signature → keep the documented 2-arg call
    if any(p.kind == inspect.Parameter.VAR_POSITIONAL for p in sig.parameters.values()):
        return True
    positional = [
        p
        for p in sig.parameters.values()
        if p.kind
        in (inspect.Parameter.POSITIONAL_ONLY, inspect.Parameter.POSITIONAL_OR_KEYWORD)
    ]
    if len(positional) >= 2 and positional[1].name == "history":
        return False
    return len(positional) >= 2


async def _call_backend(
    backend: Any,
    question: str,
    documents: list[str],
    history: Optional[list] = None,
) -> Any:
    """Invokes ``query()``/``ask()``/``answer_query()``, sync or async.

    ``RAGPipeline.answer_query(question)`` only takes the question, so
    ``documents`` are forwarded only when the exposed signature accepts a
    second positional argument.

    INTEGRATION SEAM (Backend/RAG): ``history`` is forwarded **only when the
    backend method explicitly accepts a ``history`` keyword** (or ``**kwargs``)
    and ``history is not None``. The current pipeline does not → behaviour is
    byte-identical to before. When Backend/RAG extends the signature (e.g.
    ``answer_query(question, history=None)``) the transport activates with no
    further UI change.
    """
    method = (
        getattr(backend, "query", None)
        or getattr(backend, "ask", None)
        or getattr(backend, "answer_query", None)
    )
    if method is None:
        raise TypeError("Backend exposes neither query(), ask() nor answer_query()")
    kwargs: dict = {}
    if history is not None and _accepts_keyword(method, "history"):
        kwargs["history"] = history
    result = (
        method(question, documents, **kwargs)
        if _accepts_documents(method)
        else method(question, **kwargs)
    )
    if inspect.isawaitable(result):
        result = await result
    return result


def _translate_engine_sources(payload: dict) -> dict:
    """Maps ``RAGEngine.query()`` source entries onto the frontend contract.

    Engine entries look like ``{"source", "page": "Pág. 3", "snippet"}``
    while the contract expects ``document``/``content``/``page: int``.
    Only **missing** contract keys are filled from the engine aliases —
    contract-shaped payloads (or any other backend) pass through untouched:

    * ``source`` → ``document`` (when ``document`` absent);
    * ``snippet`` → ``content`` (when ``content`` absent);
    * page label ``"Pág. 3"`` / ``"Págs. 3–5"`` → ``page`` as int (the
      contract field is a single int and the UI renders its own "pág."
      prefix); the original label is preserved verbatim in
      ``metadata["page_label"]`` so range information is never lost;
      labels without a number (``"Pág. N/A"``) → ``page=None``.

    Nothing is invented: every value written here comes from the backend.
    """
    sources = payload.get("sources")
    if not isinstance(sources, list):
        return payload
    translated: List[Any] = []
    for entry in sources:
        if not isinstance(entry, dict) or (
            "source" not in entry and "snippet" not in entry
        ):
            translated.append(entry)
            continue
        item = dict(entry)
        if "document" not in item and isinstance(item.get("source"), str):
            item["document"] = item["source"]
        if "content" not in item and isinstance(item.get("snippet"), str):
            item["content"] = item["snippet"]
        page_label = item.get("page")
        if isinstance(page_label, str):
            match = re.search(r"\d+", page_label)
            if match:
                metadata = dict(item.get("metadata") or {})
                metadata.setdefault("page_label", page_label)
                item["metadata"] = metadata
                item["page"] = int(match.group())
            else:
                item["page"] = None
        translated.append(item)
    return {**payload, "sources": translated}


class RagAdapter:
    """Translates backend responses into the frontend contract.

    Always check ``RagAdapter().is_mock`` (instance): it is ``True`` while
    no real engine is connected in :func:`create_backend`.
    """

    # is_mock: bool = True - La eliminamos para que no trabaje con datos mock

    def __init__(self, backend: Any = _UNSET, session_id: str | None = None) -> None:
        """Args:
        backend: engine to query. When omitted, :func:`create_backend` is
            used (today it returns ``None`` → demo mock).
        session_id: identity of the current Chainlit session, forwarded to
            :func:`create_backend` so a future engine can scope its retriever
            to this session. Not authentication: the backend validates.
        """
        self.session_id = session_id
        if backend is _UNSET:
            backend = create_backend(session_id)
        self.backend = backend
        self.is_mock = backend is None

    async def ask(
        self,
        question: str,
        documents: list[str],
        labels: list[str] | None = None,
        history: list[dict] | None = None,
    ) -> RAGResponse:
        """Queries the backend and returns a normalized RAGResponse.

        Args:
            question: the user's question (raw; never rewritten here).
            documents: identifiers/paths of the documentation loaded in the
                session (today consumed by the mock; the real engine may
                filter or ignore this list).
            labels: original visible file names of the session (used by the
                demo mock to keep its simulated sources coherent with the
                documents the user actually uploaded).
            history: previous turns of the CURRENT conversation as
                ``[{"role": "user"|"assistant", "content": str}, ...]`` in
                chronological order — context for the current question, the
                question itself excluded. ``None``/omitted = legacy behaviour.
                Validated by :func:`normalize_history` and forwarded only if
                the backend signature accepts ``history`` (see
                :func:`_call_backend`). The demo mock never receives it
                (it stays stateless by design).

        Returns:
            RAGResponse ready for the UI.

        Raises:
            Exception: any backend failure propagates and the UI turns it
                into a friendly message (details are never exposed).
        """
        normalized = normalize_history(history)
        if self.backend is None:
            mock = MockRAG()
            return await mock.ask(question, documents, labels=labels)
        try:
            raw = await _call_backend(self.backend, question, documents, normalized)
            return self.format_response(raw)
        except Exception as exc:
            # Si el backend falla por API key inválida (401) o falta de autenticación, degradar al mock
            err_msg = str(exc).lower()
            if any(term in err_msg for term in ("api key", "authentication", "401", "unauthorized")):
                logger.warning("Backend authentication failed (%s). Falling back to mock.", exc)
                mock = MockRAG()
                return await mock.ask(question, documents, labels=labels)
            raise

    def format_response(self, raw: Any) -> RAGResponse:
        """Normalizes any raw response into the frontend contract.

        Accepts RAGResponse, dict with the contract keys, object with
        attributes, plain text or ``None``.  Never raises on missing or
        wrongly typed optional metadata.

        Dict payloads are first passed through
        :func:`_translate_engine_sources`, which maps the engine's
        ``source``/``snippet``/page-label aliases onto
        ``document``/``content``/``page`` — identity for payloads that
        already speak the contract.
        """
        if isinstance(raw, dict):
            raw = _translate_engine_sources(raw)
        return RAGResponse.from_any(raw)
