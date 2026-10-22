# Prueba exploratoria de threshold: 256/32 y top-8

## Resultado y decisión propuesta

Se probaron diez umbrales y el control sin filtro sobre las 40 preguntas guardadas.
**0,82 es un candidato provisional para probar con el pipeline**, no un valor óptimo
validado ni una modificación aplicada al retriever.

En esta muestra solo cambia q30 (tiempo) y q31 (restaurantes): elimina sus 16
fragmentos. Las otras 38 preguntas conservan exactamente los mismos resultados.
No resuelve q24/q25 (sin respuesta), q32/q33 (fuera de alcance) ni los casos personales.
Con 0,84 ya se pierden testigos de las comparaciones anuales q20/q21.
Con 0,85, q15 queda sin documentos, pese a que antes tenía evidencia suficiente.
El umbral 0,5 no descarta ningún resultado de esta muestra.

## Método

- Colección `corpus_256_32`, k=8, ranking de la ejecución `20261004T134946547175Z`.
- Se acepta un fragmento si `cosine_similarity >= threshold`; igualdad incluida.
- La puntuación guardada es `1 - distancia cosine`, no una probabilidad.
- Filtrado posterior sobre el mismo top-8, sin nueva búsqueda ni rellenar huecos.
- No se ejecutaron embeddings, indexación ni generación LLM.
- Retención de evidencia: se exige conservar todos los IDs de cada conjunto testigo
  S de la revisión asistida. Son 22 conjuntos; no son 22 respuestas del LLM evaluadas.
  Perder un testigo no prueba que no haya otra evidencia; conservarlo no garantiza
  una respuesta correcta. Las etiquetas no son gold aprobado por el equipo.
- No hay etiquetas exhaustivas de todos los fragmentos: no se calcula precision,
  recall ni una tasa global de eliminación de ruido.
- Las preguntas personales no se consideran negativas que necesariamente deban
  quedar sin documentos: pueden necesitar evidencia para explicar reglas generales.

## Resultados

| Umbral | Fragmentos conservados /320 | Testigos completos conservados /22 | Documento /30 | Página /28 | Tokens medios | Sin respuesta: vacías /2 | Fuera de alcance: vacías /4 |
|---|---:|---:|---:|---:|---:|---:|---:|
| Sin filtro | 320 | 22 | 30 | 24 | 1944.0 | 0 | 0 |
| 0.5 | 320 | 22 | 30 | 24 | 1944.0 | 0 | 0 |
| 0.78 | 320 | 22 | 30 | 24 | 1944.0 | 0 | 0 |
| 0.8 | 308 | 22 | 30 | 24 | 1872.3 | 0 | 1 |
| 0.82 | 304 | 22 | 30 | 24 | 1847.5 | 0 | 2 |
| 0.84 | 272 | 20 | 30 | 24 | 1654.6 | 0 | 2 |
| 0.85 | 235 | 18 | 29 | 22 | 1429.5 | 0 | 3 |
| 0.86 | 181 | 14 | 24 | 19 | 1100.0 | 1 | 3 |
| 0.87 | 95 | 10 | 18 | 13 | 578.2 | 2 | 3 |
| 0.88 | 45 | 4 | 13 | 7 | 273.9 | 2 | 4 |
| 0.9 | 2 | 0 | 1 | 0 | 11.9 | 2 | 4 |

Los tokens medios corresponden al texto recuperado de las 40 preguntas, incluyendo
overlap, sin prompt/citas. Con 0,82 bajan de 1.944,0 a 1.847,5 (aproximadamente 5 %),
solo porque q30/q31 quedan vacías. No reduce el contexto de las preguntas fiscales.

## Evidencia concreta que se pierde

- 0,84, q20: posiciones 5 (0,839885) y 8 (0,837123).
- 0,84, q21: posiciones 5 (0,839270) y 8 (0,834374).
- 0,85, q02: posición 3 (0,845482), que aporta excepciones a la regla general.
- 0,85, q15: posición 1 (0,848989); desaparecen todos sus resultados.

Las comparaciones utilizan precisión completa; los valores anteriores están redondeados
solo para mostrarlos. La conservación de page-hit a 0,84 no detecta la pérdida en
q20/q21, ya que esas preguntas no tienen expected_page.

## Comprobaciones

440 comparaciones (40 preguntas x 11 condiciones) coinciden con el resultado de
`VectorRetriever.invoke`, usando store y EmbeddingService simulados y las distancias
guardadas. Se comprobó una sola llamada embed_query por invocación, top_k=8 y filtro
público. No fue una nueva búsqueda contra Chroma real ni una prueba de generación.

Se verificaron hashes de entrada, correspondencia de IDs y textos de testigos,
320 fragmentos en el control, 24/28 páginas y 22/22 conjuntos retenidos sin filtro,
y que aumentar el umbral solo quite resultados. No hubo warnings en el replay.
No se repitió la suite completa: esta tarea solo añade resultados/documentación,
sin modificar código ejecutable del proyecto.

## Límites e integración

Esta selección usa el mismo benchmark de desarrollo: necesita validación del equipo
y nuevas preguntas para estimar generalización. 0,82 se propone entre los valores
ensayados; no se afirma que sea el mejor de todos los posibles.

Un contexto vacío no garantiza abstención. Las preguntas fuera de alcance y los
casos personales requieren tratamiento del pipeline. Este experimento no modifica
su comportamiento ni sus prompts y no evalúa documentos privados.

La configuración de producción no ha cambiado: el default actual del retriever
sigue siendo top_k=4, score_threshold=0.5. Para un ensayo posterior habría que
pasar explícitamente top_k=8 y score_threshold=0.82 sobre la colección 256/32.
No confundir una propuesta experimental con un cambio ya aplicado.

## Reproducción desde los resultados guardados

El JSON detallado `threshold_sweep_256_32.json` está junto a `results.json`, fuera
del repositorio, bajo la carpeta de esta ejecución. Incluye IDs retenidos por
pregunta, categorías, testigos perdidos y resúmenes de cada umbral.
El siguiente cálculo reproduce la tabla de retención de testigos, sin modelo:

```python
import json
from pathlib import Path

# Ejecutar desde la raíz del repositorio; sustituir RUN por la carpeta de la ejecución.
run = Path(RUN)
data = json.loads((run / "results.json").read_bytes())
review = json.loads(Path("docs/retrieval_review_matrix.json").read_bytes())
labels = {r["question_id"]: r for r in review["rows"]
          if r["configuration"] == "corpus_256_32" and r["status"] == "S"}
rows = data["results"]["corpus_256_32"]["questions"]
for threshold in (None, .5, .78, .80, .82, .84, .85, .86, .87, .88, .90):
    kept_count = retained_sets = 0
    for row in rows:
        kept = {r["id"] for r in row["ranked"]
                if threshold is None or r["cosine_similarity"] >= threshold}
        kept_count += len(kept)
        label = labels.get(row["question"]["id"])
        if label:
            retained_sets += all(e["id"] in kept for e in label["evidence"])
    print(threshold, kept_count, retained_sets)
```

Resultados originales SHA-256: `b52ba84de1cbf6c9971b6108e5da0c4e0bb46d93c56497e6e05bf42428aebf04`.

Revisión de testigos SHA-256: `3a831161a167ed19d7dcede7d65aa1535f2e8d0365ce8d56ece88b4ce2ed544c`.

Barrido detallado SHA-256: `c281730c59ab937a7a9de7e6ba84ef692dcb04084f5248f4f1c4cb45bf6b9446`.
