# Evaluación inicial del retrieval

El script compara las colecciones ya verificadas, sin volver a indexar ni generar
respuestas LLM. Ejecutar desde la raíz del repositorio:

```bash
python -m scripts.evaluate_retrieval --manifest RUTA_AL_MANIFIESTO
```

Con E5 cacheado se puede anteponer `HF_HUB_OFFLINE=1` en Git Bash. El manifiesto
identifica la carpeta persistente; no hay que copiarla al repositorio ni cambiar
la colección de producción. Los resultados JSON y Markdown quedan bajo
`evaluations/` junto al manifiesto, fuera del código fuente.

## Diseño de la comparación

- Reutiliza el modelo configurado en el manifiesto y EmbeddingService.embed_query.
- Genera un vector por pregunta y reutiliza ese vector en las tres colecciones.
- Consulta VectorStore.query con el filtro público obligatorio del experimento;
  no evalúa sesiones privadas ni modifica el retriever/pipeline de producción.
- No usa expected_doc_id, expected_page, expected_section, expected_year ni las notas
  como entradas a la búsqueda. Solo se utilizan las referencias para puntuar después.
- Threshold desactivado. Obtiene un ranking top-8 por pregunta/colección y puntúa
  sus primeros 3, 4, 5 y 8 resultados. Es una comparación de prefijos de ese ranking;
  no son cuatro llamadas ANN independientes (podrían diferir según el buscador).
- Registra similitud cosine como 1 - distancia; no es una probabilidad.
- Comprueba que los registros recuperados coinciden con el manifiesto verificado.

## Qué medimos y qué no

Document-hit@k cuenta preguntas con al menos un fragmento del documento esperado:
30 preguntas evaluables en el benchmark actual. Referenced-page-hit@k exige además
page <= expected_page <= page_end: 28 preguntas. Sin etiqueta, el resultado es
no evaluable, nunca un fallo ni un acierto. Repetir chunks relevantes no multiplica
los aciertos de una pregunta. Los casos especiales se conservan con sus notas.

No son Recall@k de chunks: faltan etiquetas exhaustivas de fragmentos relevantes.
Un acierto de página no demuestra que el fragmento incluya toda la evidencia.
q19 requiere revisar varias páginas; q20/q21 no tienen página estructurada.
No se evalúan respuestas fiscales, abstención ni generación del LLM.

Se registra la suma de tokens del texto original recuperado, sin tokens especiales,
prefijos de embeddings ni formato del prompt. Incluye texto repetido por overlap.
La media inicial comprende las 40 preguntas y no es el coste total del prompt.
A igual k, tamaños mayores pueden mejorar aciertos a costa de más contexto.

Estas son decisiones experimentales, no parámetros óptimos. No se cambia el
benchmark compartido. Deben revisarse los textos de aciertos/fallos, cobertura y
coste antes de elegir una configuración. El mismo benchmark sirve de desarrollo;
no hay un conjunto independiente que permita afirmar generalización.

## Primera ejecución: 4 de octubre de 2026

Modelo: `intfloat/multilingual-e5-base`. Las 40 preguntas se ejecutaron contra
las tres colecciones; threshold desactivado. No se modificó el benchmark.


| Colección | k | Documento | Página | Tokens medios de texto (40 preguntas) |
|---|---:|---:|---:|---:|
| corpus_256_32 | 3 | 30/30 | 18/28 | 730.3 |
| corpus_256_32 | 4 | 30/30 | 19/28 | 972.7 |
| corpus_256_32 | 5 | 30/30 | 20/28 | 1214.8 |
| corpus_256_32 | 8 | 30/30 | 24/28 | 1944.0 |
| corpus_384_48 | 3 | 29/30 | 17/28 | 1115.8 |
| corpus_384_48 | 4 | 29/30 | 17/28 | 1486.8 |
| corpus_384_48 | 5 | 29/30 | 19/28 | 1858.0 |
| corpus_384_48 | 8 | 29/30 | 24/28 | 2965.1 |
| corpus_480_64 | 3 | 30/30 | 20/28 | 1400.5 |
| corpus_480_64 | 4 | 30/30 | 21/28 | 1869.8 |
| corpus_480_64 | 5 | 30/30 | 22/28 | 2337.6 |
| corpus_480_64 | 8 | 30/30 | 24/28 | 3739.8 |

No selecciona ganador: hace falta revisar la evidencia recuperada.
El detalle JSON conserva preguntas, notas y textos para esa revisión.

Los fallos de página a k=8 son distintos:

- `corpus_256_32`: q01, q04, q07, q13.
- `corpus_384_48`: q04, q05, q15, q16.
- `corpus_480_64`: q04, q05, q08, q17.

q04 falla la referencia de página en las tres configuraciones. En 480/64 se
recupera un fragmento de páginas 431–432, vecino de la referencia 430; necesita
revisión de evidencia antes de interpretarlo como fallo semántico. En q15,
384/48 recupera otro documento del corpus que podría contener información
relacionada; un fallo de documento esperado no demuestra por sí solo ausencia
de respuesta. Estas observaciones no validan el contenido fiscal.

A k=8 las tres coinciden en 24/28, con distintos errores. 256/32 usa menos
texto recuperado, pero no se ha revisado aún la integridad de la evidencia.
No hay una configuración seleccionada.

Benchmark SHA-256: `4f54578f1ac5c5ee616eb1482b4a023333e4d11096b9fc78968ab9f5472b8913`.

Manifiesto SHA-256: `393f152d36e9c54b4b252e146c96a642ba4eccccbb89167a29c404f8daef3334`.

## Revisión cualitativa inicial

Ver [revisión de evidencia](retrieval_evidence_review.md) para q01, q04, q05, q15, q16 y q19.
La muestra encuentra referencias alternativas y aciertos de página incompletos.
No modifica las métricas anteriores ni selecciona una configuración ganadora.

## Revisión cualitativa completada

La auditoría de las 40 preguntas en las tres configuraciones está en
[retrieval_review_complete.md](retrieval_review_complete.md), con 120 valoraciones
y trazabilidad en JSON. Sustituye el estado pendiente de revisión indicado en
la primera ejecución. Las métricas automáticas permanecen intactas; los juicios
asistidos no son etiquetas gold aprobadas ni una elección definitiva de parámetros.

## Experimento de umbrales

La prueba posterior mantiene 256/32 y top-8, sin regenerar resultados.
Ver [retrieval_threshold_experiment.md](retrieval_threshold_experiment.md).
Propone 0,82 como candidato experimental, sin modificar defaults ni declarar
abstención validada.
