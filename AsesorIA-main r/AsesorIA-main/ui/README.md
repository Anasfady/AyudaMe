# Asesor Fiscal IA — Frontend (UX/UI)

Frontend-only README: covers `ui/**` (interface, copy, adapter boundary,
mock) and `tests/**` (frontend tests). The general project README lives at
the repository root and is out of this document's scope.

Chainlit user interface for the RAG system. **Contains no retrieval,
embedding, prompt or LLM logic**: every query goes through the adapter.

## File structure

```
ui/
├── __init__.py            # Makes `ui` an importable package for the tests
├── app.py                 # UI orchestrator (states, validation, flow)
├── contracts.py           # Data contracts (RAGResponse, Source)
├── rag_adapter.py         # Single UI ↔ backend boundary (swap the mock here)
├── mock_rag.py            # Deterministic mock for development and demo
├── formatters.py          # All visible copy (answers, sources, states)
├── README.md              # This file
├── chainlit.md            # Welcome markdown (fallback)
├── chainlit_es.md         # Welcome markdown in Spanish (language `es`)
├── .chainlit/config.toml  # Name, language, theme, CSS/JS, file upload
├── public/
│   ├── theme.json         # Color tokens (light + dark) — ONLY place
│   ├── custom.css         # Scrollbar, selection, focus, step status chip
│   ├── custom.js          # Custom editor placeholder
│   ├── logo_light.svg     # Header logo (light theme)
│   ├── logo_dark.svg      # Header logo (dark theme)
│   └── avatar.svg         # Avatar for every message and step
└── ...

tests/
├── test_frontend_contract.py  # Contract, formatters, mock, adapter
├── test_app_helpers.py        # File validation and app.py helpers
└── test_integration_fake_backend.py  # Adapter against a fake backend (7 cases)
```

## How to run

```bash
pip install chainlit==2.12.0

cd ui
chainlit run app.py            # http://localhost:8000
```

**Always run from `ui/`**: `APP_ROOT` is the working directory, so `public/`
and `.chainlit/` resolve inside `ui/`.

## Interface states

| State | When | Copy (summary) |
|---|---|---|
| Welcome | `on_chat_start` | Identity + upload CTA + `Cómo funciona` (3 steps) + grounding limit + demo badge |
| Documentation | A file is attached | `📚 Documentación disponible · N documentos` + `✓ file` list |
| Suggestions | Upload sent without a question | `**¿Qué quieres consultar?**` + 4 `💡` actions (only until the first question) |
| No documents | Question with no files | `📚 Todavía no hay documentación cargada` + upload button |
| Processing | During the query | Step `Consultando documentos` with output `🔎 Consultando la documentación…` |
| Answer | `grounded=True` with sources | Answer + `📄 Fuentes utilizadas · N` |
| No information | `grounded=False` or no sources | `ℹ️ No he encontrado información suficiente` + reason |
| Error | Backend exception | `⚠️ No he podido conectar…` / `⚠️ Se ha producido un error técnico` |
| Empty question | Message without content | Friendly reminder with an example |

**No information ≠ error**: the first is an expected outcome of grounding;
the second is a failure and uses different messages.

## Source traceability

Every answer with sources is followed by an independent block:

```
**📄 Fuentes utilizadas · 2**

**1. manual-iva.pdf** · pág. 42 · Deducción del IVA
> "El IVA soportado es deducible cuando…"

**2. BOE-...pdf** · pág. 18 · Artículo 95
> "Se considerará deducible el IVA…"
```

- `page`, `section` and `score` are optional: fields that arrive as `null`
  are simply **omitted from the header** (no placeholder text). The
  `relevancia …` fragment only appears when the backend provides a score
  with validated semantics (never simulated by the demo).
- If the sources list is empty, **no block is emitted** (the UI never breaks).
- **Side view hygiene:** the answer also ships one `cl.Text(display="side")`
  chip per source so Chainlit's side view can open on demand. The previous
  answer's chips are removed before each new reply
  (`_clear_side_elements`), so the panel always shows only the **latest**
  answer's sources — never a mix of older ones. On screens ≤640 px the side
  view dialog is closed as soon as it appears (it would cover the chat);
  sources stay fully readable in the in-thread block above.

## Expected backend contract

```json
{
    "answer": "Texto de la respuesta...",
    "sources": [
        {
            "document": "Nombre del documento.pdf",
            "content": "Fragmento recuperado...",
            "page": 42,
            "section": "Sección relevante",
            "score": 0.94,
            "metadata": {}
        }
    ],
    "grounded": true,
    "no_answer_reason": null,
    "latency_ms": 520.0
}
```

Fields: `document` and `content` always present; `page`, `section`, `score`
and `metadata` optional (`null` tolerated). Not enough information:
`{"answer": "", "sources": [], "grounded": false, "no_answer_reason": "..."}`.

## Real contract observed (pre-integration)

> **Status: frontend prepared for real integration — the RAG pipeline is
> NOT connected yet** (no `src/rag/engine.py`; PRs #25–#28 still open).
> Verified read-only against `main` (`RAGPipeline`) and those PRs.

What the backend returns today:

```python
RAGPipeline.answer_query(question) -> {
    "answer": str,                  # always present (the LLM runs even with 0 documents)
    "source_documents": [Document], # langchain Document, may be []
}
# NO "sources", "grounded", "no_answer_reason", "latency_ms" or "score" keys.
```

Document metadata returned by the retriever: `doc_id`, `tax`, `doc_type`,
`fiscal_year`, `valid_from`/`valid_to`, `section_label`, `section_path`,
`page`, `page_end`, `source_url`, `retrieved_at`, `source_scope`,
`session_id` (when private), `chunk_index`, plus the guaranteed alias
`source = source_url or doc_id`.

Differences vs the UI contract and how the adapter normalizes them:

| Real backend | UI contract | Normalization |
|---|---|---|
| `source_documents` | `sources` | `RAGResponse.from_dict` falls back to `source_documents`. |
| `metadata.section_label` / `section_path` | `section` | fallback chain `section` → `section_label` → `section_path` → `heading`. |
| `metadata.source` (path or id) | `document` | basename only (folders/UUIDs never shown). |
| `page_content` + `page`/`page_end` | `content` + `page` | mapped directly; the full metadata dict is preserved untouched in `metadata`. |
| no `score` | `score = null` | the «relevancia» line is **omitted — never invented**. |
| no `grounded` | `grounded = true` default | `grounded` must be provided/derived by the RAG layer; the UI does not invent a grounding policy. |
| no `latency_ms` | `latency_ms = null` | not displayed. |

**Score semantics** (verified in the retrieval docs of PRs #25–#28): Chroma
cosine `distance = 1 − similarity`, so a real score would be a similarity in
**[−1, 1]** — *not* a probability. The frontend displays any provided value
**exactly as received** (no distance→similarity conversion, ever).

**`session_id`**: bound when the backend *constructs* its retriever
(`get_retriever(session_id=…)`), validated on the backend side — never per
query and never authentication. The UI supplies the identity through the
seam `create_backend(session_id=…)` (`app.py` reads
`cl.context.session.id` with a process-wide fallback).

Still pending on the backend before a real integration: create
`src/rag/engine.py`, merge PRs **#25 → #26 → #27 → #28** (the order
announced by the RAG team), signal `grounded`/abstention, validate the
session before building the retriever, and (optionally) emit scores.

## Using the mock

`mock_rag.py` is deterministic (same question → same answer):

| Keywords | Result |
|---|---|
| `iva` + `deducible` | Answer + 2 sources with full metadata |
| `303` / `autoliquidación` | Answer + 3 sources (several documents) |
| `alta` + `autónomo` | Answer + 1 source |
| `cripto` / `bitcoin` | `grounded=False`, no sources (no information) |
| `metadata` / `incompleto` | Sources with `null` metadata (UI robustness) |
| `error` / `fallo` | Raises an exception → UI error state |
| anything else | Generic answer + 1 source |

**Source coherence**: the mock receives the session's real document names
(`labels`) and binds its simulated sources to them, so the cited documents are
always the ones the user uploaded (never invented filenames). With no
uploads, it keeps its own simulated names.

**No invented scores**: every simulated source keeps `score = null`, so the
demo never shows «relevancia». That line only appears when the real backend
provides a score with validated semantics (cosine similarity).

The 🧠 badge on the welcome screen tells the user they are in demo mode
(`RagAdapter.is_mock`). Once the real engine is connected it becomes `False`
and the badge disappears.

## Integration with the RAG

### Integration point

`ui/rag_adapter.py` is the **only** point of contact. The chain is:

```
app.py  →  rag_adapter.py  →  engine.py (RAG team)   [or MockRAG, today]
```

`app.py` knows nothing about LangChain, Chroma, prompts or the LLM: only the
contract.

### 1. Which function the frontend will call

```python
async def query(question: str, documents: list[str]) -> dict | RAGResponse
# ask(...) and a synchronous implementation are also accepted;
# answer_query(question) — the real RAGPipeline signature — works too
# (documents are passed only when the exposed signature accepts them).
```

The adapter invokes it with `backend.query(question, documents)` (or `ask`,
or `answer_query(question)`), expects a sync or `await`-able result and
normalizes it with `RAGResponse.from_any(...)`.

### 2. Parameters received

| Parameter | Type | Description |
|---|---|---|
| `question` | `str` | The user's natural-language question (already validated: non-empty). |
| `documents` | `list[str]` | Names/paths of the documents loaded in the session. The engine may filter or ignore them. |

### 3. Returned structure (REQUEST / RESPONSE)

REQUEST (what the adapter sends to the engine):

```json
{
  "question": "¿Qué gastos son deducibles de un autónomo?",
  "documents": ["Manual_Renta.pdf", "modelo-303.pdf"]
}
```

RESPONSE (what the engine must return, dict or object equivalent):

```json
{
  "answer": "Los gastos necesarios para la actividad son deducibles…",
  "sources": [
    {
      "document": "Manual_Renta.pdf",
      "page": 42,
      "section": "Gastos deducibles",
      "content": "Son deducibles los gastos de suministros…",
      "score": 0.94,
      "metadata": {}
    }
  ],
  "grounded": true,
  "no_answer_reason": null,
  "latency_ms": 320
}
```

### 4. How to represent sources

Each element of `sources` provides traceability; the UI renders
document · page · section · relevance · snippet:

- `document` (**required**): name shown to the user. If a path arrives, the
  UI shows only the filename (never UUIDs or folders).
- `content` (**required**): the exact retrieved snippet (rendered as a quote).
  When missing, the UI shows *(fragmento no disponible)*.
- `page`, `section`, `score` (optional): `null` → the field is omitted from
  the header (no placeholder text is shown); relevance only appears when a
  validated score is present.
- `metadata` (optional): free dict; if it contains `source`/`page`/`section`/
  `score`, the UI uses them as fallback.

With `sources: []` the UI does **not** emit the sources block (provenance is
never invented).

### 5. How to signal `grounded=False`

```json
{ "answer": "", "sources": [], "grounded": false,
  "no_answer_reason": "sin resultados relevantes en la documentación" }
```

The UI renders it as *«No he encontrado información suficiente»* (a
responsible state, **not** a technical error). `no_answer_reason` is shown as
*Motivo: …*. `grounded` also accepts `"true"`/`"false"`; when omitted with a
`no_answer_reason` present it is interpreted as `false`.

### 6. How to communicate errors

**Raise an exception** (`raise`). The UI catches the failure inside the step
and shows a friendly message (`⚠️ Se ha producido un error técnico` or
`⚠️ No he podido conectar con el motor de consulta`), **never** a stack trace
or internal details. Returning an `answer` containing the error text is
wrong: it would be shown to the user as if it were the answer.

### Connecting `engine.py` (2 steps, only `rag_adapter.py`)

```python
def create_backend(session_id: str | None = None):
    from src.rag.engine import RagEngine   # ← RAG team import
    return RagEngine(session_id=session_id)  # scopes the retriever (backend validates)
```

Once done, adapter instances report `is_mock = False` and the welcome screen
drops the 🧠 demo badge. **`app.py`, `formatters.py` and the UI need no
changes.**

### Guaranteed normalization (tolerance)

The adapter converts to the contract without ever raising, even if the
engine delivers:

`sources: null` · a single source instead of a list · `page`/`score` as text ·
`document` as a path · LangChain-style objects (`page_content`, `metadata`) ·
`answer: null` · `grounded: "false"` · a `None` response · an already
normalized response (`RAGResponse`).

## Interface customization

| What | Where |
|---|---|
| Palette (light/dark), radii, sidebar | `public/theme.json` (HSL tokens) |
| Global styles | `public/custom.css` |
| Editor placeholder | `public/custom.js` → `¿Qué quieres consultar sobre tu documentación?` |
| Name, language, default theme, layout | `.chainlit/config.toml` |
| Brand logo and avatar | `public/logo_*.svg`, `public/avatar.svg` + `default_avatar_file_url` |
| Copy (all visible text) | `formatters.py` |

### Optional login (Google, native Chainlit)

Login uses Chainlit's own OAuth mechanism — no custom form, no user
database, no self-issued tokens. It activates only when the environment
provides credentials; without them the app starts normally with login
disabled (the welcome screen carries no login CTA in either case).

| Variable | Purpose |
|---|---|
| `CHAINLIT_AUTH_SECRET` | Session JWT secret — generate with `chainlit create-secret` |
| `OAUTH_GOOGLE_CLIENT_ID` | Google Cloud → Credentials → OAuth client ID (Web) |
| `OAUTH_GOOGLE_CLIENT_SECRET` | Same credential pair |

Redirect URI to register in Google Cloud:
`http://localhost:8000/auth/oauth/google/callback`. The callback maps the
Google profile onto `cl.User(identifier=e-mail, display_name=name)` and
rejects unknown providers or missing e-mails
(`ui/app.py` → `_oauth_callback`; covered by
`tests/test_frontend_login.py`). `.env` is loaded at startup
(`load_dotenv()`), because the Chainlit CLI does not do it.

### Conversation persistence (SQLite, native Chainlit data layer)

Threads and steps are saved to a local SQLite file (`ui/.data/chainlit.db`,
git-ignored) so conversations are durable; `ui/persistence.py` bootstraps
Chainlit's official schema (adapted to SQLite: no FKs, `tags` as JSON)
and registers the layer via `@cl.data_layer`.

| Variable | Purpose |
|---|---|
| `CHAINLIT_PERSISTENCE` | On by default; set to `0` to disable |
| `CHAINLIT_SQLITE_PATH` | Override the DB path (default `ui/.data/chainlit.db`) |

Behaviour and limits:

- **Per-user isolation is server-enforced** by Chainlit (thread author
  checks): each identity sees only its own threads; separate deployments
  use separate files. Covered by `tests/test_frontend_persistence.py`.
- **History and thread resume require login.** In open mode (no OAuth
  credentials) data is still written, but a reload starts a fresh thread
  (there is no identity to resume from) — and the console stays clean.
- Uploaded **files/elements are not persisted** (no storage client):
  attachments from older sessions do not re-render; the text of the
  conversation does.
- Schema ownership/migration (SQLite → Postgres, backups) is backend
  scope — see `.agent-local/audit/product-ux/PERSISTENCE_HANDOFF.md`.

### Important Chainlit 2.12 restriction

- The **name of a `cl.Step`** is used as the avatar identifier
  (`/avatars/<name>`) and that endpoint rejects accents and symbols → use
  only `[a-zA-Z0-9_ .-]` (e.g. `"Consultando documentos"`). Accented
  text goes in the step `output`, which does accept it.
- `cl.user_session` only exposes `get(key, default)` / `set(key, value)`.
- There is no `@cl.on_action`: use `cl.Action(name, payload, label, tooltip,
  icon)` + `@cl.action_callback("name")`.
- Exceptions must **never** escape an `async with cl.Step(...)`: the step
  itself would send `str(exc)` to the client. Catch them inside the block.
- Spontaneous file upload: `[features.spontaneous_file_upload]` in the
  config; files arrive in `on_message` as `message.elements` (with the
  original `.name` and the storage `.path`).
- **Asymmetric task events (Stop-button bug)**: Chainlit 2.12's ask flow
  sends an orphan `task_start` when an ask resolves (emitter) and action
  callbacks run outside a task context, so the composer could stay in
  "running" state (■ Stop) forever after using an action button. Workaround
  in `app.py`: `_emit_task()` wraps every action callback with a balanced
  `task_start`/`task_end` pair (guarded, never raises). Do not remove it
  without re-running the composer audit.
- `language = "ex"` must match an existing translation file (`es`, not
  `es-ES`) and `chainlit_es.md`; otherwise Chainlit logs a warning at
  startup. Both files are included → clean startup.
- Known browser console notice:
  `Missing Description or aria-describedby for DialogContent` — comes from
  Chainlit 2.12's internal bundle (Radix dialog), **not** from project code.
  It is cosmetic: it breaks neither the upload dialog nor the accessibility
  of the rest of the interface. It will disappear when Chainlit fixes it.

## Supported file types

PDF, TXT and Markdown (`.pdf`, `.txt`, `.md`), up to 50 MB per file and 5 per
message. Unknown extensions, empty or unreadable files produce a specific
error message (never a silent failure).

## Tests

```bash
python -m pytest tests/ -q
```

- `tests/test_frontend_contract.py` — contract (`Source`/`RAGResponse`), every
  formatter/copy string, mock scenarios (including source coherence with the
  uploaded labels and the no-invented-scores rule) and the adapter.
- `tests/test_app_helpers.py` — file validation, `app.py` helpers, suggestion
  actions, the balanced `_emit_task` bookkeeping and the `session_id` seam.
- `tests/test_integration_fake_backend.py` — two layers: the 7 theoretical
  contract cases (2 sources, 1 source, no sources, `grounded=False`,
  incomplete metadata, error, latency) plus tolerance variants; and the
  **real backend shape** (`answer_query` → `source_documents`: mapping,
  empty corpus, no-answer readiness, error, `session_id` forwarding, long
  answer).

No network dependencies or external services.

## UX decisions

1. Conversations are **persisted** per session user (SQLite data layer,
   see above); with login, history and thread resume work per identity.
   Without login (open mode) a reload starts a fresh thread.
   (Chainlit keeps the raw upload bytes under `ui/.files/<session>/`; nothing
   references them after the session is gone.)
2. All copy in Spanish, professional tone, no technical jargon for the user.
3. Sources always visible (no accordion) right under the answer.
4. Stack traces, keys and internal paths never reach the interface.
5. Authentication is optional and native (Google OAuth through Chainlit,
   enabled only with credentials in the environment); without them the app
   runs open. The tests make no network calls.
6. Internal step statuses (`Usado`/`Usando`) are hidden via the documented
   exception in `public/custom.css`; the user only sees the step title.

---

# Frontend handoff

Guide to connecting `src/rag/engine.py` without asking how the UI consumes
it.

## Integration point

| What | Where |
|---|---|
| Only file to touch | `ui/rag_adapter.py` → `create_backend()` |
| Data contract | `ui/contracts.py` (`Source`, `RAGResponse`) |
| Copy / states | `ui/formatters.py` (do not touch) |
| UI orchestration | `ui/app.py` (do not touch) |

## Expected engine signature

```python
async def query(question: str, documents: list[str]) -> dict:
    ...
```

- Acceptable: `ask(...)` instead of `query(...)`, a synchronous
  implementation, or the pipeline's real `answer_query(question)` (the
  adapter inspects the signature and passes `documents` only when accepted).
- `documents` = names/paths of the session documentation (the engine decides
  whether to use them for filtering).
- Returns a `dict` with the contract keys (an object with the same
  attributes or an already built `RAGResponse` also works). The real shape
  `{"answer", "source_documents"}` is already understood — see *Real
  contract observed* above.

## Response fields

| Field | Required | Semantics |
|---|---|---|
| `answer` | Yes | Answer text (Markdown allowed). `""` when there is no answer. |
| `sources` | Yes (may be `[]`) | Snippets used, with provenance. |
| `grounded` | Yes | `true` = answer grounded in documentation. `false` = not enough information. |
| `no_answer_reason` | No | Short reason in Spanish (shown when `grounded=false`). |
| `latency_ms` | No | Engine latency. |
| `sources[].document` | Yes | Visible document name (if a path arrives, only the file is shown). |
| `sources[].content` | Yes | The exact retrieved snippet. |
| `sources[].page` | No | Integer. `null` → field omitted from the header. |
| `sources[].section` | No | Text (`section_label` accepted from the real metadata). `null` → field omitted. |
| `sources[].score` | No | Float (a real score would be a cosine similarity in [−1, 1]). `null` → relevance not shown. |
| `sources[].metadata` | No | Free dict (fallback for `source`/`page`/`section`/`score`); preserved as received. |

## Expected engine behavior

1. **Grounded answer** → `grounded: true` + `sources` with at least one real
   snippet. The UI paints the `📄 Fuentes utilizadas · N` block.
2. **Not enough information** → `grounded: false`, `answer: ""` and
   `no_answer_reason`. The UI shows the ℹ️ state (not an error).
3. **Real error** → `raise`. The UI shows a friendly `⚠️` with no stack
   trace. Never return the error inside `answer`.

## Replacing the mock with the real engine

```python
# ui/rag_adapter.py
def create_backend(session_id: str | None = None):
    from src.rag.engine import RagEngine
    return RagEngine(session_id=session_id)
```

That is all: the adapter calls `RagEngine().query(...)` (or the engine's
`answer_query`), normalizes the response and `is_mock` flips to `False`
(the 🧠 demo badge disappears). `app.py`, `formatters.py` and the UI stay
unchanged.

## Minimum checks after connecting `engine.py`

```bash
python -m pytest tests/ -q      # 126 tests (contract + adapter + formatters)
cd ui && chainlit run app.py --port 8000
```

Manual check (5 minutes):

1. Upload a real PDF → `📄 Documentación disponible` appears with the
   **original filename**.
2. Question answered from that PDF → answer + `📄 Fuentes utilizadas · N`
   block with document, page, section and quote.
3. Question outside the corpus (e.g. cryptocurrencies) →
   *«No he encontrado información suficiente»* state with a reason.
4. Disconnect the engine / force a failure → friendly `⚠️`, no stack trace.
5. Welcome screen without the 🧠 badge (confirms `is_mock = False`).
6. Browser console free of errors and HTTP responses without 4xx/5xx.

If step 2/3 fails because of how `engine.py` returns the data, fix it
**inside `rag_adapter.py`** (normalization), never in the UI.
