# Configuración inicial de retrieval V1

Decisión del equipo: 256 tokens / 32 de overlap, top_k=8 y threshold=0.82.
Modelo: intfloat/multilingual-e5-base. Colección: corpus_256_32.
No son requisitos numéricos del briefing ni parámetros universalmente óptimos.
Los argumentos explícitos siguen permitiendo experimentar; threshold=None desactiva
el umbral. Se usa similitud coseno (1 - distancia de Chroma), no una probabilidad.

## Configuración y despliegue

Settings establece el chunking y nombre de colección. Retriever, RAGEngine y su
factory comparten los defaults de retrieval; el script test_rag_e2e usa esos defaults.
La UI crea el motor mediante su factory. El singleton conserva la primera configuración:
reiniciar el proceso después de cambiar parámetros o entorno.

Configurar CHROMA_DIR en el .env local con la carpeta del índice ya generado y
CHROMA_COLLECTION=corpus_256_32. No se distribuye el índice mediante Git.
Seleccionar un nombre no indexa documentos ni demuestra que su contenido sea 256/32:
verificar el manifiesto y el recuento antes del despliegue. El índice evaluado contiene
7.472 chunks. En Windows utilizar una ruta sin acentos. La ruta local de cada
compañero puede ser diferente; nunca copiar claves al repositorio.

La implementación actual de VectorStore crea una colección vacía si no existe:
una respuesta de abstención con una colección vacía NO valida el retrieval.
La V1 no cambia ese comportamiento ni implementa reindexación automática.

## Evidencia y límites

La elección usa las comparaciones del benchmark documentadas en retrieval_evaluation.md,
retrieval_review_complete.md y retrieval_threshold_experiment.md. Son evaluaciones
sobre nuestro corpus y no una validación independiente exhaustiva.

Prueba manual real realizada con Groq / openai/gpt-oss-120b:
- Modelo 303: 8 chunks, evidencia directa trimestral en página 219.
- Tiempo en Madrid: cero chunks y abstención del LLM.
- Importe personal exacto de IRPF sin datos del usuario: 8 chunks generales y
  abstención del LLM; superar el umbral no garantiza suficiencia de evidencia.

Las fuentes devueltas representan todo el contexto
recuperado, no una prueba de que cada fuente haya sustentado una afirmación.
No se modifican prompts ni se garantiza ausencia de alucinaciones. Una V1 funcional
no equivale a validar toda respuesta fiscal. Los informes de experimentos anteriores
se conservan como historial; esta nota registra la adopción de la configuración.
