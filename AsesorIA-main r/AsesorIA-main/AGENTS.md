## Project
AsesorIA — copiloto fiscal RAG para autónomos en España.

## Arquitectura
Usuario
→ Chainlit
→ ui/app.py
→ ui/rag_adapter.py
→ backend RAG

La UI NO debe conocer:
- Chroma
- embeddings
- retriever
- prompts
- LLM
- detalles internos de ingestion

## Frontend scope — Persona 4

SÍ:
- ui/app.py
- ui/contracts.py
- ui/formatters.py
- ui/rag_adapter.py
- ui/mock_rag.py
- ui/public/
- tests frontend
- documentación UX/frontend
- Playwright
- axe
- Lighthouse
- accesibilidad
- responsive
- microcopy
- diseño visual

NO:
- ingestion
- chunking
- embeddings
- Chroma
- retrieval
- prompts
- LLM
- RAG engine
- persistencia backend
- autenticación backend
- Docker
- hosting
- infraestructura
- corpus/indexación

No modificar src/ salvo que exista una dependencia de contrato frontend/backend explícitamente necesaria y claramente justificada.

## Framework
Mantener Chainlit.

NO migrar a:
- Angular
- React
- Vue
- Svelte
- otro framework web

No reescribir la aplicación.

## WebMCP
NO implementar WebMCP.
NO añadir APIs experimentales de browser agents.
NO introducir MCP runtime en la aplicación.

## Modern Web Guidance
Puede utilizarse como guía del coding agent.

NO convertir Modern Web Guidance en dependencia runtime.
NO añadirlo a requirements.txt/package.json salvo que exista una necesidad real y explícitamente aprobada.

## Diseño
AsesorIA debe seguir pareciendo:
- asistente RAG corporativo
- interfaz conversacional
- profesional
- limpia
- intuitiva
- accesible
- responsive

NO convertirlo en:
- dashboard
- ERP
- portal administrativo
- NotebookLM
- SaaS sobrecargado

No añadir componentes solo porque estén de moda.

Cada elemento nuevo debe justificar:
1. problema UX
2. beneficio
3. coste de complejidad

## Mock
El mock debe ser siempre claramente un mock.

No:
- inventar scores
- fingir fuentes reales
- fingir conexión con corpus real
- ocultar que es demo

## Backend integration
El único punto de integración frontend/backend es el adapter.

El frontend debe consumir el contrato.
No implementar backend dentro de ui/.

## Tests
Después de cambios frontend ejecutar:

python -m pytest tests/ -q

Objetivo:
0 fallos.

Cuando proceda:
- Playwright
- axe
- Lighthouse
- smoke tests
- responsive tests

## UX rules
Priorizar:

primera visita
→ documentos
→ pregunta natural
→ loading
→ respuesta
→ fuentes
→ nueva pregunta

No forzar keywords.
No añadir otro LLM/classifier para clasificar preguntas.
Las ayudas deben ser deterministas y sencillas.

## Copy
Todo texto visible debe ser:
- español natural
- profesional
- claro
- no técnico
- no repetitivo

Nunca mostrar al usuario:
- stack traces
- mensajes internos
- workarounds
- detalles del agente
- mensajes de implementación
- "Usado"
- mensajes técnicos que no aporten valor

## Git
Nunca trabajar directamente sobre main.

Antes de cambios:
git status

Antes de finalizar:
git diff
python -m pytest tests/ -q

No hacer commits gigantes ni reescrituras innecesarias.