# Criterios de aceptación — AsesorIA

## Alcance del sistema

AsesorIA responde preguntas de fiscalidad para autónomos en España.

Las respuestas deben basarse únicamente en la documentación disponible en el corpus indexado.

El corpus público está compuesto por documentación procedente de fuentes oficiales, principalmente:

- Agencia Estatal de Administración Tributaria (AEAT).
- Boletín Oficial del Estado (BOE).

Cada documento incorporado al corpus debe estar identificado mediante sus metadatos correspondientes y registrado en `data/sources.csv`.

La información que no esté respaldada por la documentación recuperada se considera fuera del alcance de respuesta del sistema.

---

## 2. Criterios de aceptación por categoría

| # | Situación | Comportamiento esperado | Cómo se valida |
|---|---|---|---|
| **CA-1** | Pregunta con información disponible en el corpus | El sistema debe generar una respuesta basada en los fragmentos recuperados y mostrar las fuentes utilizadas. | Pruebas con preguntas de la categoría `direct` de `data/eval/benchmark.json`. |
| **CA-2** | Pregunta sin información suficiente en el corpus | El sistema debe indicar que no dispone de información suficiente y no debe inventar una respuesta. | Pruebas de la categoría `no_answer` del benchmark. |
| **CA-3** | Pregunta que requiere información personal del usuario | El sistema puede proporcionar la regla general disponible en la documentación, pero no debe presentar una valoración personalizada como una conclusión definitiva. | Pruebas de la categoría `personal_case`. |
| **CA-4** | Pregunta fuera del ámbito del sistema | El sistema debe identificar la consulta como `out_of_scope` y rechazarla de forma clara y educada. | Pruebas de la categoría `out_of_scope`. |
| **CA-5** | Información recuperada de varias fuentes | El sistema debe poder utilizar varios fragmentos relevantes para construir una respuesta cuando sea necesario. | Preguntas del benchmark que requieren información procedente de varios documentos. |
| **CA-6** | Fuente utilizada en una respuesta | Toda respuesta fundamentada debe mostrar las fuentes que han servido para construirla. | Comprobación de `sources` en la respuesta y revisión visual de la interfaz. |
| **CA-7** | Fragmento recuperado | La fuente mostrada debe corresponder realmente al contenido recuperado y no debe inventarse información de procedencia. | Comparación entre el fragmento mostrado y el contenido recuperado. |
| **CA-8** | Documento no legible o no procesable | El pipeline debe detectar documentos cuyo contenido no pueda extraerse correctamente y generar un error o advertencia controlada. | Pruebas del loader con documentos no compatibles o sin texto extraíble. |
| **CA-9** | Formato de documento no soportado | El sistema debe rechazar el archivo e indicar que el formato no está soportado. | Prueba con una extensión no incluida en los formatos admitidos. |
| **CA-10** | Documento con tablas | Las tablas relevantes deben poder extraerse y conservar su información de forma estructurada para su posterior procesamiento por el sistema RAG. | Comparación entre tablas del PDF y resultado de `extract_tables()`. |
| **CA-11** | Documento con cabeceras o pies repetidos | El proceso de limpieza debe eliminar elementos repetidos que puedan introducir ruido en la recuperación, sin eliminar contenido normativo relevante. | Revisión de documentos procesados mediante `clean_text()` y `remove_repeated_lines()`. |
| **CA-12** | Documento incorporado al corpus | El documento debe disponer de un `doc_id`, tipo de documento, ámbito, fuente y metadatos suficientes para identificar su procedencia. | Revisión de `data/sources.csv` y de los metadatos generados durante la ingesta. |

---

## 3. Criterios específicos de corpus e ingesta

Respecto a la ingesta documental, se establecen además los siguientes criterios:

### CA-I1 — Fuentes oficiales

Los documentos públicos incorporados al corpus deben proceder de fuentes oficiales identificables.

La información de procedencia debe quedar registrada en:

```text
data/sources.csv
```

Como mínimo, el registro debe permitir identificar:

* nombre del archivo;
* `doc_id`;
* área temática;
* tipo de documento;
* fuente oficial;
* fecha de recuperación.

### CA-I2 — Carga de documentos

El loader debe permitir procesar los formatos definidos por el proyecto:

* PDF;
* TXT;
* Markdown.

Los documentos PDF deben procesarse página por página para conservar la información de localización.

### CA-I3 — Control de errores de extracción

Si un PDF no contiene texto extraíble, el sistema debe detectar la situación y generar un `UnreadableDocumentError`.

Los formatos no soportados deben generar un `UnsupportedFileTypeError`.

El pipeline no debe continuar silenciosamente con un documento que no haya podido procesarse correctamente.

### CA-I4 — Limpieza del texto

El proceso de limpieza debe:

* corregir palabras separadas artificialmente por saltos de línea;
* normalizar espacios;
* conservar los saltos de párrafo relevantes;
* eliminar cabeceras y pies repetidos cuando corresponda.

La limpieza no debe modificar ni eliminar información normativa relevante.

### CA-I5 — Extracción de tablas

Las tablas de los documentos PDF deben tratarse de forma independiente cuando sea necesario.

La información extraída debe transformarse a un formato estructurado que pueda ser utilizado posteriormente por el pipeline RAG.

Las tablas que no contengan información útil deben poder descartarse para evitar introducir ruido.

### CA-I6 — Metadatos de procedencia

Los documentos y fragmentos procesados deben conservar información suficiente para poder localizar posteriormente su origen.

Los metadatos contemplados por el proyecto incluyen:

* `doc_id`;
* `tax`;
* `doc_type`;
* `section_label`;
* `section_path`;
* `page`;
* `source_url`;
* `retrieved_at`;
* `source_scope`;
* `session_id` cuando se trate de documentación privada.

### CA-I7 — Preguntas de validación

El conjunto de evaluación debe contener preguntas representativas del caso de uso.

Las preguntas deben cubrir, como mínimo:

* preguntas con respuesta disponible;
* preguntas sin información suficiente;
* preguntas que requieren información específica del usuario;
* preguntas fuera del ámbito del sistema.

El conjunto se mantiene en:

```text
data/eval/benchmark.json
```

---

## 4. Trazabilidad

Toda respuesta fundamentada debe permitir identificar las fuentes utilizadas.

La interfaz debe mostrar, cuando estén disponibles:

* documento;
* página;
* sección;
* fragmento recuperado;
* relevancia de la fuente.

La fuente mostrada debe corresponder al contenido realmente recuperado por el sistema.

Cuando no existan fuentes suficientes, el sistema no debe fabricar información de procedencia.

---

## 5. Comportamiento ante ausencia de información

Cuando el sistema no encuentre información suficiente para responder:

```text
grounded = false
sources = []
```

La interfaz debe informar al usuario de que no se ha encontrado información suficiente.

La ausencia de información no debe tratarse como un error técnico.

El sistema no debe completar la respuesta utilizando conocimiento general del modelo cuando la información necesaria no esté respaldada por el corpus.

---

## 6. Documentación privada

Los documentos privados subidos por un usuario deben identificarse mediante:

```text
source_scope = private
```

y asociarse a su correspondiente:

```text
session_id
```

Los documentos privados deben permanecer aislados de otras sesiones.

La información privada no debe aparecer en las fuentes o resultados de recuperación de una sesión diferente.

---

## 7. Tono de las respuestas

Las respuestas de AsesorIA deberán ser:

* claras;
* directas;
* comprensibles;
* fundamentadas en la documentación recuperada;
* libres de afirmaciones que no estén respaldadas por las fuentes.

El sistema debe presentar la información como contenido obtenido de la documentación disponible y no como asesoramiento profesional personalizado.

La interfaz debe informar de forma visible de que AsesorIA no sustituye a un asesor fiscal.

---

## 8. Comportamientos no aceptables

No será aceptable:

* inventar cifras, porcentajes, plazos, artículos o requisitos;
* responder utilizando información que no esté respaldada por el corpus;
* mostrar una fuente que no haya sido utilizada para generar la respuesta;
* ocultar un error de extracción de documentos;
* eliminar información relevante durante la limpieza;
* mezclar documentos privados entre diferentes sesiones;
* responder como si una consulta estuviera fundamentada cuando no existen fragmentos relevantes.

---

## 9. Proceso de validación

1. Las preguntas de evaluación se mantienen en `data/eval/benchmark.json`.
2. El pipeline de ingesta se valida sobre los documentos definidos en el corpus.
3. Se comprueba que los documentos pueden cargarse correctamente.
4. Se comprueba la limpieza del contenido extraído.
5. Se comprueba la extracción de tablas cuando existan.
6. Se comprueba la conservación de los metadatos de procedencia.
7. El retriever se valida comprobando que devuelve fragmentos relevantes para las preguntas del benchmark.
8. El sistema RAG se valida comprobando que las respuestas están fundamentadas en los fragmentos recuperados.
9. Las preguntas sin información suficiente y fuera de alcance se utilizan para comprobar que el sistema rechaza correctamente consultas que no puede fundamentar.

---

## 10. Trabajo pendiente: anonimización de datos personales

Actualmente no debe considerarse que el sistema anonimiza automáticamente datos personales antes de indexarlos.

Como trabajo pendiente se deberá implementar un mecanismo de anonimización que permita detectar y tratar, como mínimo:

* NIF;
* CIF;
* NIE;
* IBAN;
* email;
* teléfono;
* nombres de personas.

La solución deberá aplicarse tanto al texto extraído directamente de los documentos como a la información obtenida de tablas de PDF.

Hasta que esta funcionalidad esté implementada y validada, **no deberá presentarse la anonimización de PII como una funcionalidad disponible del sistema**.

### Estado

```text
TODO — Implementar redact_pii()
TODO — Validar anonimización en texto
TODO — Validar anonimización en tablas extraídas de PDF
TODO — Evaluar detección de nombres propios
```

### Riesgo

Los documentos privados que contengan información personal podrían conservar dichos datos durante el proceso de indexación mientras esta funcionalidad permanezca pendiente.

Esta limitación deberá quedar documentada en la reflexión ética y, si procede, en el aviso de privacidad de la interfaz.

