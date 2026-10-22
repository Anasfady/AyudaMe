# AGENTS.md — Frontend & UX (Persona 4)

Ámbito exclusivo de trabajo de **Juan — Persona 4: Frontend & UX**.
Este archivo documenta solo las reglas del frontend. No impone reglas sobre
otras personas ni sobre el backend.

## Identidad del rol

- Persona 4 — Frontend & UX.
- Archivos de este ámbito: `ui/app.py`, `ui/contracts.py`,
  `ui/formatters.py`, `ui/rag_adapter.py`, `ui/mock_rag.py`,
  `ui/guidance.py`, `ui/public/`, tests de frontend y documentación UX.
- Fuera de este ámbito (NO tocar): `src/ingestion/`, `src/indexing/`,
  `src/retrieval/`, `src/rag/`, embeddings, Chroma/vector DB, chunking,
  prompts, LLM, pipeline RAG, persistencia backend, autenticación backend,
  Docker, hosting, infraestructura, corpus/indexación.
- Si una mejora depende de otra persona: documentar la dependencia,
  NO implementarla por cuenta propia.

## Framework

- Chainlit 2.12 es el framework actual. Se mantiene.
- NO migrar a Angular, React, Vue, Svelte ni reescribir el frontend.
- NO iniciar una reescritura: la mejora buscada es UX, UI, accesibilidad,
  responsive, calidad visual e integración limpia.

## Frontera frontend/backend

- El único punto de integración es `ui/rag_adapter.py`.
- `app.py` NO debe conocer Chroma, embeddings, retriever, prompts, LLM ni
  detalles internos de ingesta.
- NO introducir backend dentro de `ui/`.
- NO inventar scores, fuentes ni metadata de procedencia.
- NO inventar capacidades del backend (grounded, persistencia, login).
- Si el backend real aún no expone un contrato suficiente: documentar la
  dependencia, no inventar una solución.

## Mock

- El mock (`ui/mock_rag.py`) debe identificarse siempre como demo.
- NO inventar scores (`score = null`).
- NO fingir fuentes reales ni conexión con el corpus real.
- NO ocultar que es una demostración.

## Diseño

- AsesorIA debe seguir pareciendo un asistente RAG corporativo:
  conversacional, profesional, limpio, intuitivo, accesible y responsive.
- NO convertirlo en dashboard, ERP, portal administrativo, NotebookLM ni
  SaaS sobrecargado.
- NO añadir cards, menús, sidebars, widgets, animaciones ni gráficas por
  moda. Cada elemento nuevo debe justificar: problema UX, beneficio y
  coste de complejidad.
- NO implementar funcionalidades que el backend aún no soporte (login
  ficticio, persistencia de chat, etc.).
- NO implementar WebMCP ni MCP runtime en la aplicación.

## Accesibilidad y responsive

- Priorizar accesibilidad (teclado, focus, contraste, labels, jerarquía)
  y responsive (desktop y ~420 px).
- Usar Playwright, @axe-core/playwright y Lighthouse cuando proceda.
- No perseguir puntuaciones artificiales: priorizar problemas reales de UX.

## Tests

Tras cualquier cambio de frontend:

```bash
python -m pytest tests/ -q
```

Objetivo: 0 fallos. No modificar tests existentes para hacerlos pasar:
si un cambio rompe un test, el cambio es el que está mal.

## Copy

- Todo texto visible en español natural, profesional, claro y no técnico.
- Nunca mostrar al usuario stack traces, mensajes internos, workarounds,
  «Usado», mensajes de implementación ni detalles del agente.

## Git

- Trabajar en `feature/frontend` (nunca directamente sobre `main`).
- Antes de cambios: `git status`. Al finalizar: `git diff` + tests.
- No hacer commits gigantes ni reescrituras innecesarias.

## Skills de apoyo

- `.agents/skills/frontend-ux/SKILL.md`
- `.agents/skills/accessibility/SKILL.md`
- `.agents/skills/modern-web/SKILL.md`
- Modern Web Guidance es referencia del agente, NO dependencia runtime
  (nunca añadirlo a `requirements.txt` ni a `package.json`).
