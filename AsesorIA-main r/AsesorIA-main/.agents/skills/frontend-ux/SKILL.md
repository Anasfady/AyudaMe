# Frontend UX Skill — AsesorIA

## Propósito
Procedimiento reusable para el coding agent (Persona 4) trabajando en el frontend de AsesorIA. Este skill encapsiona buenas prácticas, reglas de alcance y pasos reutilizables.

## 1. Inspeccionar antes de modificar
1. Ejecutar `git status` y confirmar rama `feature/frontend` o equivalente.
2. Revisar la estructura: `ui/`, `ui/public/`, `tests/`.
3. Identificar el estado UX afectado (bienvenida, carga, chat, respuesta, fuentes, error).
4. Confirmar que no se toca `src/`, backend, ingesta, vectorstore, embeddings, retrieval, prompts, LLM.

## 2. Identificar estado UX afectado
Estados posibles:
- Primera visita (`on_chat_start`)
- Sin documentos
- Carga de documento (`AskFileMessage`)
- Documento disponible (`📚 Documentación disponible`)
- Usuario escribiendo pregunta
- Estado de carga (`cl.Step(name="Consultando...")`)
- Respuesta con fuentes
- No hay información suficiente (`ℹ️ No he encontrado información suficiente`)
- Error técnico (`⚠️ Se ha producido un error técnico`)
- Nueva pregunta

## 3. Conservar arquitectura
- No migrar a Angular/React/Vue/Svelte.
- Mantener Chainlit 2.12.
- No implementar WebMCP ni MCP runtime.
- No tocar `src/ingestion/`, `src/indexing/`, `src/retrieval/`, `src/rag/`.
- No modificar `ui/rag_adapter.py` salvo contrato frontend/backend explícito.
- Mantener `ui/contracts.py` y `ui/formatters.py` intactos salvo corrección de copy técnico.

## 4. Modificar mínimo
- Solo cambiar lo necesario para resolver el problema UX identificado.
- Preferir editar `ui/public/custom.css` o `ui/public/custom.js` antes que rehacer componentes.
- Mantener nombres de clase `-ias-*` y prefijos CSS.
- Mantener comportamiento determinista del mock (`MockRAG`).
- Si se toca `app.py`, mantener `@cl.set_starter_categories`, `@cl.action_callback`, flujo de pasos (`Step`), y micro-decisiones (`_decision_kind`, `_ask_decision`).

## 5. Comprobar responsive
- Probar viewport desktop (~1400px).
- Probar viewport móvil 420px.
- Verificar que respuestas largas, fuentes y nombres de documento no se cortan.
- Confirmar que FAB y panel lateral siguen visibles/accesibles.

## 6. Comprobar accesibilidad
- Contraste (ver skill accessibility).
- Nombres accesibles en botones y chips.
- Focus visible con `:focus-visible`.
- Navegación por teclado (Tab order).
- `aria-label` en elementos interactivos.
- Encabezados jerárquicos (`h1`, `h2`, etc.).
- Estados de error y loading accesibles.

## 7. Ejecutar tests
```bash
python -m pytest tests/ -q
```
Objetivo: 0 fallos.

Cuando proceda:
- `playwright test` (si está configurado).
- `pytest --cov` para cobertura.
- Revisar específicamente `test_native_ux.py` y `test_frontend_contract.py`.

## 8. Revisar visualmente
- Levantar `chainlit run app.py` en `localhost:8000`.
- Recorrer flujo: primera visita → upload → pregunta → respuesta → fuentes.
- Verificar light y dark theme.
- Confirmar que no hay copy técnico visible (stack traces, workarounds, "Usado", mensajes de implementación).
- Verificar consistencia visual (espacios, jerarquía, colores).

## 9. Informar cambios
Al finalizar, documentar:
- Archivos modificados.
- Tests antes/después.
- Problemas de accesibilidad encontrados.
- Problemas UX encontrados.
- Cambios visuales realizados.
- Cualquier bloqueo externo.
- Tareas que pertenecen a otro rol (backend, infra, docs).