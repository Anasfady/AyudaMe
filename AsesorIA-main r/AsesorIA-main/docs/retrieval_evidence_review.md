# Revisión inicial de la evidencia recuperada

Esta muestra de seis casos se conserva como detalle. La revisión de las 40
preguntas está completada en [retrieval_review_complete.md](retrieval_review_complete.md).
Las referencias a trabajo pendiente siguientes describen el estado de esta muestra inicial.

Revisión cualitativa asistida, pendiente de validación del equipo. Muestra dirigida
de seis preguntas; no constituye una evaluación exhaustiva ni modifica las
etiquetas o puntuaciones del benchmark. Las observaciones describen el corpus
congelado del experimento, no una validación de normativa fiscal vigente.

## Trazabilidad y criterio

Ejecución: `20261004T134946547175Z`, bajo
`C:/Users/gemac/AsesorIA-data/chroma_db/corpus_runs/a664191542dd460d8933243cc2cb938b/evaluations/`.
Consultar `results.json` para preguntas, notas, ranking y textos completos.
Los hashes de benchmark y manifiesto figuran en `retrieval_evaluation.md`.
Las páginas citadas son físicas, numeradas desde 1; posiciones del ranking desde 1.

Se distingue entre evidencia suficiente para la pregunta literal, evidencia parcial
y ausencia de evidencia directa suficiente en los fragmentos revisados.
Un resultado alternativo puede responder al dato solicitado sin cubrir todas las
 condiciones de las notas. No se recalculan métricas con estos juicios preliminares.

## q01: una página alternativa contiene el porcentaje solicitado

En 256/32, posición 4, IRPF parte 1, página 14, aparece explícitamente el 5 por 100
para gastos de difícil justificación en estimación directa simplificada en 2025.
Se contrastó con las páginas originales 14 y 449. La página 449, referencia del
benchmark, desarrolla además el rendimiento neto positivo, el límite de 2.000 euros
y otras condiciones que ese fragmento de página 14 no recoge.

Juicio: evidencia alternativa suficiente para el porcentaje literal desde k=4;
no equivale a cubrir todas las condiciones de la nota. El fallo automático de
página sigue siendo un fallo respecto a la referencia, no prueba de ausencia de respuesta.
Alcance: se revisó este fragmento, no se calificaron todos los resultados de q01.

ID: `a2f746c1de7d36a7946da2875433340f9053213d2338ebdefc23b1516a5e66ea`.

## q04: proximidad de páginas con evidencia parcial

Se revisaron los ocho resultados de las tres configuraciones y las páginas
430–431 del manual IRPF parte 1. La página 430 incluye la regla sobre cotizaciones
del titular al RETA. En 480/64, posición 1, páginas 431–432, se recupera la
regularización de cuotas: cantidades adicionales o devoluciones y su tratamiento.
Es información relacionada, pero falta la explicación principal que responde a
la deducibilidad general. Los top-8 de 256/32 y 384/48 no aportan evidencia directa
suficiente para esa pregunta en los textos revisados.

Juicio: evidencia parcial en 480/64; no dar por completa la respuesta por recuperar
una página vecina. No se modifica el fallo de página de las tres configuraciones.

ID del resultado parcial: `0af4cb53c20f9aae5ead4fe46bbe5e4d9171bf1e10d4205402368951f1f13d96`.

## q15: otro documento contiene el dato solicitado

En 384/48, posición 1, `reta_regimen_cotizacion_2022`, páginas 59–60, el fragmento
incluye el encabezado de 2025 y la fila de tabla reducida, tramo 1, con base mínima
653,59. Se contrastó esa fila con la página 16 de la orden de cotización 2025,
documento esperado. El fragmento también contiene datos de otro año; es necesario
asociar la cifra con su encabezado. La posición 2 contiene tablas de años anteriores.

Juicio: el primer resultado aporta evidencia alternativa para ese dato concreto,
aunque documento y página esperados fallen. Esto no demuestra equivalencia global
entre documentos ni validez de cualquier otra fila. Alcance: posiciones 1 y 2 y
páginas originales indicadas; no calificación exhaustiva de todos los resultados.

ID de posición 1: `35d8711a3678c4c1b1d2e931ce34c66e17348a99e08118559d2abec03d001812`.

## q19: acierto de página sin evidencia completa

La pregunta necesita cinco componentes: contingencias comunes, profesionales,
MEI, cese de actividad y formación. Las tres configuraciones aciertan documento
y página ya a k=3. Se revisaron los top-8 completos de las tres.

En 480/64, posición 2, página 16 de la orden, se reúnen los tres primeros componentes.
Sin embargo, ninguno de los tres top-8 reúne también el cese y la formación con
sus tipos y contexto RETA correctos. Las páginas originales 29 y 30 contienen,
respectivamente, 0,90 para cese y 0,10 para formación en el contexto solicitado.
El 0,10 adicional que aparece en página 16 corresponde a otro concepto: no debe
reutilizarse como formación solo porque coincida numéricamente.

Juicio: evidencia parcial en las tres configuraciones incluso a k=8. Recuperar
la página de referencia no basta para fundamentar la suma pedida. Las métricas
automáticas de página permanecen intactas: miden presencia, no suficiencia.

ID de 480/64, posición 2: `1362b69403a55723fcea4756618fb3e0a9a24b814eec04c8472c9458628927e2`.

## Consecuencias para la elección de parámetros

Esta muestra detecta limitaciones de las etiquetas de documento/página y casos de
evidencia incompleta. No permite ordenar definitivamente las tres configuraciones.
Antes de elegir, conviene completar una revisión consistente de las preguntas con
referencias, aceptar alternativas justificadas con el equipo y comparar evidencia
suficiente junto con tokens de contexto. Cualquier etiqueta nueva debe conservarse
separada del benchmark original y validarse explícitamente.

No se ha cambiado el corpus, el benchmark, el threshold, el chunking ni el pipeline.

## Ampliación: q05, pie de página y respuesta parcial

Se inspeccionó el ranking de las tres configuraciones y el texto de los fragmentos
situados en páginas 427–431 del manual IRPF parte 1; se contrastaron las páginas
originales 427 y 428. No se calificó el contenido completo de los demás resultados.

En 256/32, posición 1, el fragmento 427–428 comienza con el pie de la página 427.
El cuerpo corresponde a las especialidades de contratación de familiares de la
página 428. Así, el acierto automático de página 427 no demuestra que se haya
recuperado la explicación general de sueldos y salarios de esa página.
El fragmento aporta un caso particular, no la enumeración completa solicitada.
ID: `9dfa2706c907685c96f01ae4ea1518cf3e544660a6c9ee55a02c095858ba0159`.

En 480/64, posición 1, páginas 430–431, sí aparece el apartado de otros gastos de
personal, con formación, seguros y obsequios, aunque falle la página esperada 427.
Es evidencia parcial útil, no cobertura completa de las categorías de la nota.
ID: `02144ecf6b1eb16723de6fde3ff4d2bc89d59ed3059394fca2b75c8caadbd696`.
En 384/48, posición 5, el fragmento 430–431 comienza ya en gastos del titular:
no hay que confundir su RETA con los gastos de personal de la pregunta.

Este hallazgo no demuestra un error en el cálculo de páginas: el pie pertenece
realmente a 427. Señala ruido del texto extraído y una limitación de usar únicamente
la intersección de páginas como señal de evidencia. Cualquier cambio de limpieza
se evaluaría en otro experimento, sin alterar esta línea base.

## Ampliación: q16, la cifra y el año deben permanecer vinculados

Se revisaron los ocho resultados de 384/48 y la página original 60 del RDL de 2022.
La primera posición contiene una fila con 950,98 para la tabla general de 2024,
y después el encabezado 2025 con la tabla reducida. Esa coincidencia numérica
no basta para justificar la tabla general de 2025 solicitada.

La posición 6 contiene la tabla general correspondiente a 2025, pero su encabezado
año no está dentro de ese fragmento. Puede reconstruirse su continuidad combinando
las posiciones 1 y 6: comparten las tres filas de la tabla reducida y la procedencia
59–60/60. El PDF original confirma la continuidad. Hay evidencia alternativa
reconstruible a k=8, con contexto repartido; no se considera un fragmento
independiente inequívoco ni se presupone que un LLM vaya a unirlo correctamente.
A k=3/4/5 falta la posición 6 y la cifra aislada de otro año no es evidencia suficiente.

ID de posición 1: `35d8711a3678c4c1b1d2e931ce34c66e17348a99e08118559d2abec03d001812`.
ID de posición 6: `82de6caf1a40346922f4f024cfec13aed6cd943570a841bcfea0d80abbfa0182`.

Esto justifica estudiar la conservación del contexto de tablas en un experimento
posterior. No justifica cambiar ahora los tamaños ni marcar automáticamente
cualquier aparición de la cifra esperada como respuesta válida.
