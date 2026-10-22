# Auditoría inicial del benchmark de retrieval

Auditoría del corpus local, sin modificar benchmark.json ni elegir parámetros ganadores.
Reproducir: `python -m scripts.audit_retrieval_benchmark`.
El informe con hashes de los PDF, conteos y extractos se guarda fuera de Git en
`chroma_db/benchmark_audit.json`. El JSON original tiene BOM UTF-16; se lee desde bytes
para respetar su codificación sin reescribir el trabajo del equipo.

## Resultado y límites

40 preguntas: 28 direct, 2 year_dependent, 2 no_answer, 4 personal_case y 4 out_of_scope.
30 tienen expected_doc_id; 28 tienen expected_page. q20/q21 no tienen página estructurada,
aunque sus notas remiten a las páginas 59–60 del RDL de cotización.
Los siete PDF están disponibles; todas las referencias a documentos existen y las
páginas declaradas están dentro del rango del PDF.

Se inspeccionaron los extractos y pies de las páginas referenciadas. La numeración de
los manuales y de los BOE consolidados consultados coincide con la posición física.
En el RDL 13/2022 publicado en el BOE, la página física 11 lleva el número impreso
107447; la 59 lleva 107495 y la 60, 107496. Usar SIEMPRE posición física 1-based para
comparar con page/page_end. No aplicar un desplazamiento basado en el número BOE.
Esto verifica la correspondencia de referencias, no que una sola página contenga
necesariamente toda la evidencia necesaria para cada respuesta.

El corpus suma 2.847 páginas: IRPF parte 1 (1.448), parte 2 (634), IVA (350), LGSS (274),
LETA (39), RDL cotización (64) y Orden de cotización (38).
IRPF parte 2 y LGSS no tienen preguntas con expected_doc_id asignado: deben permanecer
en el corpus como posibles resultados, pero el benchmark no mide su cobertura temática.

## Medición inicial propuesta

- Document-hit@k: en las 30 preguntas con referencia documental, al menos un resultado
  coincide con expected_doc_id. Es una medida muy gruesa, no demuestra respuesta correcta.
- Referenced-page-hit@k: en las 28 con página, al menos un resultado del documento
  esperado cumple page <= expected_page <= page_end. Indicar explícitamente denominador.
- No denominar ninguna de estas medidas Recall@k de chunks: no tenemos un conjunto
  exhaustivo de fragmentos relevantes. Tampoco coincidencia de página demuestra que
  el texto recuperado contenga la evidencia; requiere revisión de contenido.
- No filtrar las búsquedas usando expected_doc_id, expected_page o expected_section:
  son etiquetas para puntuar después, nunca pistas proporcionadas al retriever.
- Mantener exactamente las mismas preguntas, PDFs, limpieza y modelo al comparar
  256/32, 384/48 y 480/64. Primera comparación sin threshold, para k=3,4,5,8.
  Registrar también tokens totales recuperados: igual k no implica igual presupuesto
  de contexto. No seleccionar parámetros óptimos sin resultados y revisión.
- Los 10 casos especiales se registran aparte. No exigir automáticamente cero
  resultados: casos personales o fuera de alcance pueden recuperar textos relacionados
  sin que estos autoricen una respuesta. Abstención del LLM y estado de respuesta
  pertenecen a una evaluación distinta. El retriever devuelve Document, no estados.

## Referencias que necesitan anotación adicional

- q19: expected_page=16, pero la nota exige componentes de las páginas 16,29,30.
  Un acierto en 16 NO acredita evidencia completa para el cálculo. Separar ese diagnóstico.
- q20/q21: comparan dos años; la nota apunta a 59 y 60. Proponer grupos de evidencia
  por año, revisados antes de incorporar anotaciones adicionales. No rellenar silenciosamente
  el benchmark compartido ni reducir una comparación de dos años a acertar una página.
- q04/q05/q06/q23/q40: las notas mencionan continuaciones o rangos de páginas.
  Una página esperada es una referencia mínima, no una lista exhaustiva de relevantes.
- q08: la página 226 incluye una regla de traslado por días inhábiles que la nota
  simplifica al expresar un plazo concreto. Señalarlo al revisar respuestas; no usar
  esa nota como validación fiscal automática.
- expected_section es texto descriptivo; nuestra detección de secciones PDF no está
  implementada. No evaluar igualdad literal con section_label/path ni inyectar títulos
  del benchmark en los chunks.

## Siguiente paso

Acordar estas medidas de referencia y registrar por separado los casos de evidencia
múltiple. Después auditar la limpieza del resto de documentos e indexar el corpus en
colecciones por configuración. Esta revisión no ejecuta embeddings ni retrieval y no
produce resultados de calidad.
