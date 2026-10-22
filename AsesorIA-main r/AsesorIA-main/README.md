# AsesorIA

**[Español](#español) · [English](#english)**

---

## Español

AsesorIA — Sistema corporativo de preguntas y respuestas mediante RAG para la
consulta fiscal, contable y normativa de autónomos en España, garantizando
trazabilidad y mitigación de alucinaciones.

### Frontend (ui/)

Interfaz web Chainlit: carga de documentación, chat, respuestas y
**trazabilidad de fuentes** (documento, página, sección y fragmento exacto),
con panel de fuentes desplegable y tema azul corporativo (claro/oscuro).

```bash
pip install -r requirements.txt
cd ui
chainlit run app.py        # http://localhost:8000
```

- Tests del frontend: `python -m pytest tests/ -q`
- Documentación: [`ui/README.md`](ui/README.md) — estados de UX, sistema
  visual, contrato de integración y guía para conectar el backend RAG.
- Estado: **frontend integrado y probado; backend RAG pendiente de
  integración** (la UI funciona sobre un mock de demostración, etiquetado
  como tal, hasta conectar el motor real en
  `ui/rag_adapter.py → create_backend()`).

### ⚡ Integración del Motor RAG y Notas de Ejecución

- **Acceso directo al corpus preindexado:** Los usuarios pueden realizar consultas sobre la normativa fiscal y laboral base (RETA, LGSS, IRPF, IVA) desde el primer momento, sin necesidad de subir documentos manualmente a la sesión.
- **Visualización de métricas de rendimiento:** Cada respuesta generada por `RAGEngine` incluye la medición de latencia extremo a extremo en milisegundos (`⏱️ Latencia: X ms`) al pie del mensaje.
- **Trazabilidad de fuentes:** Los fragmentos citados se muestran como botones interactivos (`cl.Text(display="side")`) al pie del mensaje, desplegando el texto normativo exacto en el cajón lateral derecho al hacer clic.
- **Modo Mock desacoplado para CI y Tests:** `RagAdapter` detecta de forma inteligente si `GROQ_API_KEY` está ausente o si se están ejecutando pruebas con claves dummy (`test`/`mock`), degradando limpiamente a `MockRAG` (`is_mock = True`). Esto permite que los tests unitarios y suites de CI pasen sin requerir credenciales externas activas.
- **Requisito en entornos Windows:** Chainlit persiste en disco los elementos laterales de los mensajes. En Windows, para evitar errores de sistema (`WinError 3`), la aplicación asegura automáticamente la ruta `.files/`, aunque se puede crear manualmente en la raíz del proyecto:
  ```bash
  mkdir -p .files
  ```
- **Dependencias de visualización:** Los widgets de gráficos interactivos requieren `plotly`. Asegúrate de tenerlo instalado en tu entorno virtual:

  ```Bash
  pip install plotly
  ```

---

## English

AsesorIA — Corporate RAG question-answering system for tax, accounting and
regulatory queries by freelancers (_autónomos_) in Spain, ensuring
traceability and mitigating hallucinations.

### Frontend (ui/)

Chainlit web interface: document upload, chat, answers and **source
traceability** (document, page, section and exact snippet), with a
collapsible sources panel and corporate blue theme (light/dark).

```bash
pip install -r requirements.txt
cd ui
chainlit run app.py        # http://localhost:8000
```

- Frontend tests: `python -m pytest tests/ -q`
- Documentation: [`ui/README.md`](ui/README.md) — UX states, visual system,
  integration contract and handoff to connect the RAG backend.
- Status: **frontend integrated and tested; RAG backend pending integration**
  (the UI runs on a demo mock, labeled as such, until the real engine is
  connected in `ui/rag_adapter.py → create_backend()`).

### Expanded Version in English (for the main repository README)

````markdown
### ⚡ Backend Integration & Execution Notes

- **Pre-indexed Corpus Access:** Users can query the base legal and tax corpus (RETA, LGSS, IRPF, IVA) immediately upon startup without needing to upload local files first.
- **Latency Metric Display:** Answers rendered by `RAGEngine` include an end-to-end latency metric in milliseconds (`⏱️ Latencia: X ms`) at the bottom of the response message.
- **Source Traceability & Side Panel:** Cited regulatory excerpts are displayed as interactive source chips (`cl.Text(display="side")`) below the answer, opening the full context and snippet in Chainlit's right-hand inspection drawer upon click.
- **Decoupled Mock Fallback for CI & Testing:** `RagAdapter` intelligently checks for valid credentials. If `GROQ_API_KEY` is missing or set to dummy testing keys (`test`/`mock`), it gracefully falls back to `MockRAG` (`is_mock = True`), allowing unit tests and CI pipelines to pass seamlessly without external API dependencies.
- **Windows Environment Prerequisite:** Chainlit stores message side elements locally. On Windows environments, the application ensures recursive folder creation for `.files/` to prevent filesystem path errors (`WinError 3`). You can also ensure its presence manually:

  ```bash
  mkdir -p .files
  ```
````

- **Visualization Dependencies:** nteractive chart widgets require `plotly`. Install it within your virtual environment:

  ```bash
  pip install plotly
  ```
