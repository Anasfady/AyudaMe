# UX / UI Architecture — AsesorIA (Chainlit 2.12)

Owner: Persona 4 · Frontend & UX Engineering
Scope: `ui/**` only (see MISIÓN MAESTRA §1–§45)
Status: Phase 1 + Phase 2 implementation record

---

## 1. Context and goals

AsesorIA is a Chainlit-based fiscal copilot for Spanish self-employed
workers (`autónomos`). The assistant ships as a mock-mode demo today
(`ui/mock_rag.py`); the real retrieval engine is backend-owned and out of
scope for the frontend.

Phase 1 + Phase 2 redesign the first-run experience around three pillars:

| Pillar | Decision (product-approved) |
|---|---|
| Welcome surface | Landing-style hero (h1 + tagline + prompt) + 3 suggestion chips + FAB menu that appears after the first exchange |
| Product name | **AsesorIA** (display), `ui/` remains the package name |
| Login | Native Google OAuth (`cl.oauth_callback`, env-gated); no fake or disabled CTA on the welcome |
| Palette | Warm sand + forest green (`public/theme.json`) |

Hard constraints for every change:

1. **Zero regressions.** Baseline captured before editing: 160 tests green
   (pre-merge), 284 tests green after merging `main` into
   `feature/frontend`. Existing tests are never modified or disabled; if a
   change breaks one, the change is wrong. Approved exceptions (Persona 4
   brief, owner decision): the `test_app_helpers.py` assertion that pinned
   the removed «cierra solo» workaround copy was inverted (FASE 12); and
   conversation persistence — initially prohibited by the brief — was
   requested mid-work and approved interactively (SQLite data layer,
   see §7).
2. **Incremental, no rewrites.** Existing modules keep their structure.
3. **CSS namespacing.** Every class we own starts with `-ias-`; we do not
   target Chainlit's selectors (one documented exception, §6).
4. **Defensive JS.** `public/custom.js` is idempotent (id guards), feature-
   toggled by DOM availability, and observes mutations so re-renders can
   never duplicate nodes.

---

## 2. Native Chainlit 2.12 API — feasibility matrix (verified against installed package)

| UX goal | Native API | Verdict |
|---|---|---|
| Starter questions in categories | `@cl.set_starter_categories` + `cl.StarterCategory` / `cl.Starter` | Full support (`callbacks.py:281-316`, exported) |
| Side-panel sources (click to open) | `cl.Text(display="side")`, `cl.Pdf(display="side")` | Full support (`ElementDisplay = Literal["inline","side","page"]`, `element.py:45`) |
| Micro-decisions with buttons | `cl.AskActionMessage(content, actions=[cl.Action...], timeout=…)` | Full support (`timeout=90` default, `raise_on_timeout` opt-in) |
| Charts | `cl.Plotly(name, figure=go.Figure(...), display="inline")` | Full support (needs `plotly` in requirements — added) |
| Themed palette | `public/theme.json` injected by server (`server.py:374-379`) | Full support |
| Custom HTML islands | `cl.CustomElement(props=...)` | Available, not needed for this phase |
| Persistent conversation | data layer | **Not configured** — out of scope (see §7) |

Verified exports in `chainlit.__init__`: `Text`, `Pdf`, `Plotly`, `Action`,
`AskActionMessage`, `Starter`, `StarterCategory`, `set_starter_categories`.

---

## 3. Phase 1 — native first-run (`ui/app.py`)

### 3.1 Starter categories

`STARTER_CATEGORIES` mirrors the custom layer (same 3 × 9 questions, same
Spanish wording — the hero chips take the first question of each category,
the FAB menu shows all nine) so native chips and injected UI never diverge:

```python
@cl.set_starter_categories
async def starter_categories(user=None, *_args):
    return STARTER_CATEGORIES
```

Icons use Lucide names available to Chainlit: `percent`, `wallet`,
`clipboard-list`.

### 3.2 Side-panel sources (hybrid, zero-regression)

Two layers, both rendered for grounded answers:

1. **Interactive layer.** `_source_elements(response)` appends one
   `cl.Text(name="Fuente N: doc", content=fmt.format_source(...),
   display="side")` per retrieved chunk to the answer message (plain text,
   no `language`, no markdown markers). Chainlit renders those chips in its
   side view (`#side-view-title` / `#side-view-content`), which opens
   automatically when chips arrive.
2. **In-thread record (kept).** `_sources_panel(response)` still renders the
   collapsed `cl.Step(name="Fuentes utilizadas N")` with
   `fmt.format_sources_block`.

Side-view hygiene (UX audit):

- **Pruning.** Chainlit's side view is thread-wide, so chips used to
  accumulate: each answer stacked its sources on the previous ones («Fuente 3»
  showing five mixed entries) and stale sources stayed beside later
  no-information/error answers. `_render_response` now calls
  `_clear_side_elements()` (removes the previous answer's `cl.Text` via
  `Element.remove()`) before sending the new reply, then
  `_remember_side_elements()` stores the fresh list — the panel always shows
  only the **latest** answer's sources.
- **Mobile ≤640 px.** The same view renders as a modal dialog with backdrop
  that covers ~85 % of the screen on every answer. `custom.js`
  (`closeMobileSideView`) closes it the moment it opens (CSS zeroes the
  animation); sources stay fully readable in the in-thread step. Desktop keeps
  the docked side pane (openable/closable from Chainlit's header toggle).

Why the hybrid: the E2E scripts (smoke/probe/screenshot) assert on the step
title, and existing tests lock `format_sources_block` and
`_source_elements(display="side")`. Removing either layer would break them;
the rule is *fix my code, never the tests*. The step stays collapsed
(`auto_collapse=True`) so the thread remains tidy.

Failure handling: chip construction is wrapped per-source and pruning is
wrapped per-element — a malformed source or a failed removal can never block
the answer.

### 3.3 Micro-decision flow

`_decision_kind(question)` is a pure matcher over `normalize_query`:

| Trigger family | Buttons |
|---|---|
| Trimestres ("¿Cómo presento los trimestres?") | T1 · T2 · T3 · T4 · Ver criterios generales |
| Estimación ("¿Qué estimación debo elegir?") | Directa · Objetiva · Ahora no |

Wiring in `_handle_message`, after the ambiguity guard and before
`_answer_question`:

```python
kind = _decision_kind(content)
if kind:
    label = await _ask_decision(kind)          # cl.AskActionMessage, timeout=60
    if label:
        await cl.Message(content=f"📅 {label}", type="user_message").send()
await _answer_question(content)
```

Design rules: cancel/timeout → `None` → normal answer (the question is
never lost); the chosen label is echoed as a `user_message` for traceability.
The matcher requires "trimestr" + presentation context so "¿Cuándo se
presenta el modelo 303?" (smoke test) never triggers a popup. Construction
errors are caught (tests call `_handle_message` outside a session).

### 3.4 Charts

`RAGResponse` gained an optional `chart: dict | None` (contract-level, fully
backwards compatible: `from_dict`/`from_any` default it to `None`).
`_chart_element(response)` renders `{"title","labels","values","y_label"}`
as a `cl.Plotly` bar chart, ahead of the source chips in the message
element list. Missing plotly, malformed numbers or no session → the widget
is skipped and the textual answer still renders. `plotly>=5.18.0` was added
to `requirements.txt` under the Frontend section.

Mock scenarios for IRPF and IVA ship demo charts; all other scenarios are
untouched.

---

## 4. Phase 1 — welcome content (`ui/mock_rag.py`)

Nine starter questions map to deterministic mock scenarios:

| # | Question | Scenario |
|---|---|---|
| 1 | Gastos deducibles | existing (#7) |
| 2 | Presentar trimestres | **new** |
| 3 | IRPF y facturas | **new** |
| 4 | Tarifa plana | **new** |
| 5 | Regularización anual | **new** |
| 6 | Base de cotización | **new** |
| 7 | Darse de alta | existing (#3) |
| 8 | Empleo por cuenta ajena | **new** |
| 9 | Baja / cese de actividad | **new** |

New scenarios are inserted where keyword collisions were checked first
(irpf+factura before the general IRPF branch; the rest after obligation
#10), so no existing test or suggestion path changes behaviour. Source
metadata uses the real corpus documents from `data/sources.csv`
(`ManualRenta2025*`, `Manual_IVA_2025.pdf`, `LETA_20_2007.pdf`,
`RDL_08_2015_LGSS.pdf`, `RDL_13_2022_*`, `PJC_178_2025_*`).

---

## 5. Theme — warm sand / forest green (`ui/public/theme.json`)

All colour lives in HSL tokens; Chainlit merges them at runtime.

| Token | Light | Dark |
|---|---|---|
| `--background` | `40 35% 96%` (warm sand) | `150 12% 9%` |
| `--primary` | `152 45% 26%` (forest green) | `152 45% 46%` |
| `--accent` | `45 75% 88%` (soft amber) | `45 40% 26%` |
| `--sidebar-background` | `152 38% 15%` | `150 30% 10%` |
| `--muted-foreground` | `100 8% 40%` | `40 12% 64%` |

Radii keep `0.5rem`. Dark mode inverts the relationship (green-tinted
surfaces, sand text) instead of being a plain grey scale.

---

## 6. CSS + JS layer (`ui/public/custom.css`, `custom.js`)

### 6.1 CSS

- Global polish updated to the new palette: scrollbars, `::selection`,
  `:focus-visible`, `blockquote`, `strong`, `hr` fallbacks switched from
  blue (`221 83%`) to green/sand — the token still wins when present.
- Components under the reserved `-ias-` prefix:
  `.-ias-welcome`, `.-ias-greeting`, `.-ias-sub`, `.-ias-prompt`,
  `.-ias-sug-label`, `.-ias-grid`, `.-ias-card` (suggestion chip),
  `.-ias-skip` (skip link), `.-ias-fab` (+ `-fab-wait` hidden state),
  `.-ias-panel` (`-head`, `-close`, `-menu-group`, `-menu-item`).
- Documented exception (kept from Phase 0): the `[id^="step-"] >
  span:first-child` rule hides Chainlit's internal "Usado/Usando" chip by
  public id only; if markup changes, the rule stops applying (cosmetic).
- Mobile (≤ 640 px): `.-ias-fab` sits `10.5rem` and `.-ias-panel` `14rem`
  above the bottom, so the FAB never covers the send button nor clips the
  composer; the side-view dialog gets `animation-duration: 0` so
  `closeMobileSideView()` closes it instantly.

### 6.2 custom.js

Defensive by construction:

- **Idempotent:** every injection checks its id first
  (`ias-welcome-block`, `ias-fab`, `ias-panel`), so the `MutationObserver`
  can re-run `apply()` safely (self-heals if the thread re-renders). Every
  DOM write is guarded (create-if-missing, set-if-absent, move-only-if-
  displaced): an unconditional move would re-trigger the observer and loop
  forever.
- **Anchored:** the hero inserts before the native welcome message
  (anchor preference: the "Asesor Fiscal IA" identity line, fallback
  "Cómo funciona"; both excluded when the text lives inside our own
  `-ias-` UI, so FAB-menu items can never hijack the anchor; final
  fallback: do nothing).
- **Dispatch:** `sendQuestion()` uses the native value setter + `input`
  event + synthetic `Enter` keydown — the same path as real keystrokes.
- **Chips, not cards:** the hero offers one light suggestion chip per
  topic (first question of each category, `-ias-card -ias-chip`); the
  full set of nine lives in the FAB menu. Probes confirmed Chainlit 2.12
  renders no native starter-chip DOM on the empty thread (`starterLike`
  is empty), so nothing competes with the hero. The native
  `STARTER_CATEGORIES` remain registered in `app.py` as the
  accessible/fallback path pinned by tests.
- **FAB visibility:** `syncFabVisibility()` keeps the FAB hidden while the
  thread only holds the welcome message (`.step` count < 2) by toggling
  `-ias-fab-wait` and closing the panel; it appears from the first
  exchange onwards — the hero already offers the first suggestions.
- **Skip link (WCAG 2.4.1):** `ensureSkipLink()` injects `#ias-skip`
  («Saltar al contenido») as the first tab stop, targeting the thread
  scroller (`tabindex=-1` + id), so keyboard users jump straight to the
  conversation.
- **Accessibility layer (axe-verified):** `lang="es"`, Spanish `aria-label`s
  for every icon-only Chainlit button — `new-chat`/`upload`/`chat-submit`
  resolved through `BUTTON_LABELS` (forced, overwriting Chainlit's generic
  «Acción»), the scroll-to-bottom `lucide-arrow-down`, the copy/edit message
  actions and the side header's `lucide-arrow-left` (`labelIconButtons()`;
  unknown icons fall back to a generic "Acción"), the invalid
  `role="presentation"` removed, names for unnamed file inputs, an
  `aria-label` on the composer textarea mirroring the placeholder
  (`labelComposerInput()` — a placeholder is not a label), the skip link
  (see above), the hero `<h1>` plus an sr-only `<h2>` right after it
  (`ensureHeadingChain()`, so the steps' `<h3>` don't skip a heading
  level), `role="main"` on the thread scroller — resolved through the
  message content with `.closest()`, never by class list alone —,
  `role="region"` on `#message-composer` and
  `role="contentinfo"` on the watermark (axe «region»), `tabindex=-1` on our
  FAB/panel while an ancestor is `aria-hidden`, and `closeMobileSideView()`
  (see §3.2).
- **Stick-to-bottom:** `MutationObserver` growth detection on the thread
  scroller (found via `.ai-message`) scrolls only when the user is near the
  bottom or interacted in the last 8 s — fixes the post-upload confirmation +
  suggestions landing behind the composer, without ever fighting a user who
  scrolled up.

Contents: hero (`<h1>` «AsesorIA» + tagline «Consulta tu documentación
fiscal con respuestas claras, trazables y basadas en fuentes.» + prompt
«¿Qué quieres consultar?» + label
«Puedes empezar por:» + 3 suggestion chips), followed by the native
welcome message (identity «Asesor Fiscal IA», upload action
«Cargar documentación», «Cómo funciona», grounding note, demo-mode
notice). No login CTA, no "2 minutes" workaround note, no tagline
duplication.

---

## 7. Data & privacy (verified, for README accuracy)

| Layer | Behaviour |
|---|---|
| Uploaded files | `ui/.files/<session>/<id>` (Chainlit defaults, `config.py:61`), deleted on session close (`session.py:271,426`) and on server shutdown (`server.py:191`); `.gitignore` covers `.files/` |
| Session state | In-memory `cl.user_session` (`app.py`) plus durable threads/steps in SQLite (see below) |
| Mock engine | Reads only contract fields — never file contents (`mock_rag.py`) |
| Conversation persistence | **SQLite via Chainlit's native data layer** (`ui/persistence.py`, `@cl.data_layer` → `SQLAlchemyDataLayer`); DB at `ui/.data/chainlit.db` (git-ignored), official schema adapted to SQLite (no FKs — upstream issue #1788, `tags` as JSON), opt-out `CHAINLIT_PERSISTENCE=0`. Per-user isolation enforced server-side (author checks, `server.py` → `is_thread_author`); history/resume require login. Elements/files are not persisted (no storage client). TTLs (`session_timeout=3600`) still govern in-memory state |

Consequence: there is **no login CTA at all** — the welcome carries no
authentication promise. Login is the native Google OAuth flow of
Chainlit (`ui/app.py` → `_oauth_callback`, registered only when
`OAUTH_GOOGLE_CLIENT_ID/SECRET` exist). Conversations persist per user;
in open mode (no credentials) data is still written but a reload starts a
fresh thread because there is no identity to resume from. The fake
«Próximamente» CTA and the «2 minutos» workaround copy are gone (FASE 12).

---

## 8. Roadmap mapping

| Item | Phase | Where |
|---|---|---|
| Merge `main` → `feature/frontend`, clean | 1 | git (no conflicts; 284 green) |
| Starter categories (3 × 9) | 1 | `app.py` |
| Sources → `display="side"` + kept step | 1 | `app.py` |
| `AskActionMessage` micro-decisions | 1 | `app.py` |
| `plotly` + `cl.Plotly` charts | 1 | `requirements.txt`, `contracts.py`, `mock_rag.py` |
| Warm sand/green palette | 2 | `theme.json` |
| `-ias-*` CSS layer | 2 | `custom.css` |
| Welcome cards + FAB (defensive) | 2 | `custom.js` |
| This document | 1+2 | `docs/ux-ui-architecture.md` |
| Auth/save contract | later | backend (out of scope) |
| Thread persistence / data layer | later | backend + config (out of scope) |

---

## 9. Verification protocol

1. `python -m pytest tests/ -q` — full suite, **zero** modifications to
   existing tests (new behaviour covered by any new file, e.g.
   `tests/test_native_ux.py`).
2. E2E trio against `localhost:8000` (`.agent-local/temp/`):
   `smoke_socketio.py` (20 checks), `probe_ux.py` (12 checks),
   `screenshot_cdp.py` (visual review: cards vs native chips, palette,
   side chips).
3. Visual review items: welcome hierarchy, card hover states, FAB position
   above the composer, side drawer usability, light + dark palettes.

---

## 10. Conversational history contract

Status: **implemented on the UI side** (Persona 4); consumption pending on
Backend/RAG. Scope of this section: the UI→RAG boundary only — no query
rewriting, no contextual retrieval, no history-aware prompt exists yet
(see the ownership split below).

### Ownership — UI (Persona 4)

- Retrieve the conversation turns of the **current session only**;
- normalize and validate them at the boundary;
- apply the size window;
- transport them to `rag_adapter.ask(..., history=...)`.

### Ownership — Backend/RAG

- turn `question + history` into a standalone query (query rewriting);
- decide how history is used;
- perform contextual retrieval (`retriever.invoke(standalone_query)`);
- incorporate history into the prompt;
- produce the contextual answer.

### Contract

```python
await adapter.ask(
    question,                 # raw user question (never rewritten by the UI)
    documents,
    labels=None,
    history=None,             # optional; None = legacy behaviour
)
```

`history` format (chronological, JSON-serializable, nothing else):

```python
[
    {"role": "user" | "assistant", "content": str},
    ...
]
```

- The UI **excludes the in-flight question** (it is passed separately) and
  UI-only notices (welcome, orientation, errors — tagged
  `metadata["ias_ui_notice"]` at creation).
- Source: Chainlit's public `cl.chat_context` — a per-session list keyed by
  `session.id` (conversations never mix), populated with the incoming user
  message *before* `on_message` runs, with every sent message, and with the
  steps of a resumed thread.

### Validation and window

`rag_adapter.normalize_history()` (deterministic):

- `None`/non-list → `None`; empty list → `[]` (never raises);
- only `dict` entries with `role` ∈ {`user`, `assistant`} and non-empty
  stringifiable `content` survive; everything else is dropped;
- chronological order preserved byte-for-byte — the UI never rewrites;
- window: **last `HISTORY_WINDOW = 20` messages** (~10 round-trips: enough
  for follow-up references, small enough for any LLM context; Backend may
  re-trim).

### Transport gate (seam)

`_call_backend()` forwards `history=` **only if the backend method accepts a
`history` keyword** (or `**kwargs`). Current `RAGPipeline.answer_query(question)`
does not → behaviour is unchanged. `_accepts_documents()` will not confuse a
future `answer_query(question, history=None)` second slot with `documents`
(documents travel positionally only when the 2nd parameter is not named
`history`).

### Not the UI's responsibility

The UI does **not** implement: query rewriting, contextual retrieval,
history-aware prompts, semantic memory, or answering follow-ups by itself.
It only transports context. Persisted threads ≠ conversational memory, and
document rehydration on thread reload is a separate problem (not addressed
here).

### Backend/RAG TODO (handoff)

```text
UI/Adapter DONE:
  history transport (build → validate → window → ask(history=))

Backend/RAG TODO:
  history consumption (answer_query(history=...))
  query rewriting (question + history → standalone question)
  standalone retrieval (retriever.invoke(standalone))
  history-aware prompt ({history} / rewritten question)
  real E2E with the 5-question acceptance script + negative test
```
