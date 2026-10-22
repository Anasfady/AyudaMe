# 🏛️ AsesorIA

**Español** 

---

## 🇪🇸 Español

**AsesorIA** es un sistema corporativo avanzado de preguntas y respuestas basado en la arquitectura RAG (Generación Aumentada por Recuperación). Está diseñado específicamente para la consulta fiscal, contable y normativa de autónomos en España, garantizando una trazabilidad absoluta y la mitigación estricta de alucinaciones.

El motor de conocimiento se fundamenta exclusivamente en textos legales oficiales preindexados, tales como la *Ley 37/1992 del Impuesto sobre el Valor Añadido*[cite: 30] y el *Real Decreto 1619/2012 sobre obligaciones de facturación*[cite: 2]. Esto asegura que cada respuesta generada por el LLM esté anclada en la legislación vigente y nunca invente deducciones o normativas.

### 🌟 Características Principales y Gobernanza

* **Acceso Directo al Corpus Preindexado:** Los usuarios pueden consultar de inmediato la normativa fiscal y laboral base (RETA, LGSS, IRPF, IVA) sin necesidad de subir documentos locales a la sesión.
* **Trazabilidad de Fuentes (Grounding):** Los fragmentos citados aparecen como botones interactivos (`cl.Text(display="side")`). Al hacer clic, se despliega el texto normativo exacto (documento, página, sección y fragmento) en el cajón lateral derecho de Chainlit.
* **Transparencia y Rendimiento:** Cada respuesta generada por `RAGEngine` incluye una métrica de latencia extremo a extremo (`⏱️ Latencia: X ms`) al pie del mensaje.
* **Modo Mock Desacoplado para CI/CD:** El `RagAdapter` detecta de forma inteligente si la `GROQ_API_KEY` está ausente o si se están ejecutando pruebas con claves dummy (`test`/`mock`), degradando limpiamente a `MockRAG` (`is_mock = True`). Esto permite que los tests unitarios y las suites de integración continua pasen sin requerir credenciales externas activas.

### 💻 Frontend y Ejecución (`ui/`)

La interfaz web está construida con **Chainlit**, presentando un tema azul corporativo (claro/oscuro), panel de fuentes desplegable y chat interactivo.
*(Documentación adicional de UX/UI en `ui/README.md`)*

**Dependencias y Requisitos:**

1. Instalar dependencias generales y de visualización de gráficos interactivos:
```bash
pip install -r requirements.txt
pip install plotly

```


2. **Requisito en entornos Windows:** Chainlit persiste en disco los elementos laterales de los mensajes. En Windows, para evitar errores de ruta en el sistema de archivos (`WinError 3`), la aplicación asegura automáticamente la ruta `.files/`, aunque se puede crear manualmente en la raíz del proyecto:
```bash
mkdir -p .files

```



**Ejecución y Tests:**

```bash
cd ui
chainlit run app.py        # Disponible en http://localhost:8000
python -m pytest tests/ -q # Ejecución de tests del frontend

```

*Estado actual: Frontend integrado y probado. El backend RAG funciona sobre un mock de demostración (etiquetado como tal) hasta conectar el motor real en `ui/rag_adapter.py -> create_backend()`.*

### 🛡️ Calidad, Ética y Defensa

La validación de que el sistema cumple con las directrices de privacidad (RGPD) y que los umbrales de recuperación evitan el *data leakage* y las alucinaciones recae en nuestro equipo de QA.
**QA, Ethics & Defense Lead:** MD ABDUR RAHMAN NAHIAN.

---

## 🇬🇧 English

**AsesorIA** is a corporate RAG (Retrieval-Augmented Generation) question-answering system tailored for tax, accounting, and regulatory queries for freelancers (*autónomos*) in Spain. It ensures full traceability and strictly mitigates hallucinations by grounding its answers in official legal frameworks, such as the *VAT Law 37/1992*[cite: 30] and the *Billing Regulations Royal Decree 1619/2012*[cite: 2].

### 🌟 Key Features & Backend Integration Notes

* **Pre-indexed Corpus Access:** Users can immediately query the base legal and tax corpus (RETA, LGSS, IRPF, IVA) upon startup, with no local file uploads required.
* **Source Traceability & Side Panel:** Cited regulatory excerpts appear as interactive source chips (`cl.Text(display="side")`) below the answer. Clicking them opens the full context and exact snippet in Chainlit's right-hand inspection drawer.
* **Latency Metric Display:** Answers rendered by the `RAGEngine` include an end-to-end latency metric in milliseconds (`⏱️ Latencia: X ms`) at the bottom of the response message.
* **Decoupled Mock Fallback for CI & Testing:** `RagAdapter` intelligently checks for valid credentials. If `GROQ_API_KEY` is missing or set to dummy testing keys (`test`/`mock`), it gracefully falls back to `MockRAG` (`is_mock = True`), allowing unit tests and CI pipelines to pass seamlessly without external API dependencies.

### 💻 Frontend & Execution (`ui/`)

Built with **Chainlit**, the web interface features document upload capabilities, a collapsible sources panel, and a corporate blue theme (light/dark).
*(Further UX/UI documentation in `ui/README.md`)*

**Dependencies & Setup:**

1. Install general and interactive chart dependencies:
```bash
pip install -r requirements.txt
pip install plotly

```


2. **Windows Environment Prerequisite:** Chainlit stores message side elements locally. On Windows environments, the application ensures recursive folder creation for `.files/` to prevent filesystem path errors (`WinError 3`). You can also ensure its presence manually:
```bash
mkdir -p .files

```



**Execution & Testing:**

```bash
cd ui
chainlit run app.py        # Runs on http://localhost:8000
python -m pytest tests/ -q # Frontend tests

```

*Status: Frontend is integrated and tested. The RAG backend runs on a labeled demo mock until the real engine is connected in `ui/rag_adapter.py -> create_backend()`.*

### 🛡️ Quality Assurance, Ethics & Defense

Ensuring the system delivers accurate, legally sound advice without hallucinations—while respecting GDPR and tax secrecy—is managed by our QA team.
**QA, Ethics & Defense Lead:** MD ABDUR RAHMAN NAHIAN.