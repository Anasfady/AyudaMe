# Revisión cualitativa completa del benchmark

## Alcance y criterio

Se han revisado las 40 preguntas en las tres configuraciones (120 valoraciones),
utilizando el ranking top-8 guardado. Es una auditoría asistida de evidencia,
pendiente de validación humana; no son etiquetas oficiales ni una evaluación del LLM.
Se inspeccionaron fragmentos candidatos, referencias alternativas y casos problemáticos;
no se etiquetó individualmente la relevancia de cada uno de los 960 resultados.
Los casos N se apoyan en lectura del top-8 completo. P significa que no se acredita
suficiencia, no una prueba exhaustiva de ausencia de toda evidencia posible.

La valoración sigue la pregunta literal y el ámbito del benchmark. No exige que
una pregunta de un dato incluya todas las condiciones posibles de una respuesta
fiscal extensa. Para listas y comparaciones exige los componentes solicitados.
La coincidencia de una cifra sin concepto, régimen o año correcto no se acepta.
Se permiten referencias alternativas justificadas. No se valida normativa vigente.

- **S**: evidencia explícita suficiente identificada para la pregunta literal.
- **P**: evidencia parcial o relacionada; suficiencia no acreditada.
- **A**: contexto reconstruible pero ambiguo, o referencia que requiere validación.
- **N**: sin evidencia directa suficiente en el top-8 leído.
- **E**: caso especial; comportamiento de abstención/personalización no evaluado.

Los números entre paréntesis son posiciones de fragmentos testigo, no el k mínimo
necesario ni etiquetas de todos los fragmentos. Por ello no se derivan nuevas
métricas por k de esta tabla. El JSON adjunto registra IDs, páginas y hashes.

## Matriz de las 40 preguntas

| Pregunta | 256/32 | 384/48 | 480/64 |
|---|---|---|---|
| q01 | S (4) | S (8) | S (1) |
| q02 | S (1,3) | S (1,4) | S (1) |
| q03 | S (1) | S (1) | S (1) |
| q04 | N | N | P (1) |
| q05 | P (1) | P (5) | P (1) |
| q06 | S (1) | S (1) | S (6) |
| q07 | N | S (6) | S (8) |
| q08 | A (7) | A (7) | A (1,2,3) |
| q09 | S (7) | S (3) | S (1) |
| q10 | S (2) | S (1) | P (1,2) |
| q11 | S (1) | P (7) | S (1) |
| q12 | S (6) | S (7) | S (2) |
| q13 | P (1,5) | P (1,2) | P (1,2,5) |
| q14 | P (1,4) | P (3,6) | S (3) |
| q15 | S (1) | S (1) | S (2) |
| q16 | S (1) | A (1,6) | S (1) |
| q17 | S (2) | S (3) | P (1,2,4) |
| q18 | P (1,4,6) | P (1,3) | S (3) |
| q19 | P (3) | P (3) | P (2) |
| q20 | S (5,8) | S (1,2) | P (4,7) |
| q21 | S (5,8) | P (1,2) | P (4,6) |
| q22 | S (1) | S (3) | S (5) |
| q23 | S (6) | S (5) | S (1) |
| q24 | E (1) | E (1) | E (1) |
| q25 | E (1) | E (1) | E (1) |
| q26 | E (1) | E (1) | E (1) |
| q27 | E (1) | E (1) | E (1) |
| q28 | E (1) | E (1) | E (1) |
| q29 | E (1) | E (1) | E (1) |
| q30 | E (1) | E (1) | E (1) |
| q31 | E (1) | E (1) | E (1) |
| q32 | E (1) | E (1) | E (1) |
| q33 | E (1) | E (1) | E (1) |
| q34 | S (2) | S (1) | S (1) |
| q35 | S (1) | S (1) | S (1) |
| q36 | S (4) | S (5) | S (2) |
| q37 | S (1) | S (1) | S (1) |
| q38 | S (7) | S (2) | S (5) |
| q39 | S (1) | S (2) | S (1) |
| q40 | S (1,4) | S (3) | S (1) |

## Justificación por pregunta

### q01 — ¿Qué porcentaje de gastos de difícil justificación se aplica en estimación directa simplificada en 2025?

Porcentaje literal con contexto de 2025. 256/32 y 480/64 ofrecen página alternativa 14; S no implica cubrir todas las condiciones de la nota. La revisión previa era parcial: no establecía el primer rango posible.

### q02 — ¿Cuándo puede considerarse afecto un automóvil de turismo a una actividad económica?

Regla IRPF de uso exclusivo y excepciones: 256/32 y 384/48 las reparten entre fragmentos; 480/64 las reúne. La pregunta no nombra IRPF: se sigue el ámbito de su referencia, sin mezclar reglas IVA.

### q03 — ¿Qué porcentaje de los suministros de mi vivienda puedo deducir si trabajo desde casa?

Regla completa: 30 % de la proporción de superficie, salvo prueba de porcentaje distinto; no 30 % de todos los suministros.

### q04 — ¿Puedo deducirme las cuotas del RETA en mi declaración del IRPF de 2025?

256/32 y 384/48: revisión de top-8 sin regla directa suficiente. 480/64: regularización de cuotas, pero falta la regla principal de deducibilidad.

### q05 — ¿Qué gastos de personal son deducibles en el IRPF de 2025 para un autónomo con empleados?

Evidencia parcial: familiares en 256/32; gastos del titular en 384/48; otros gastos de personal en 480/64. El pie de 427 genera un page-hit sin la explicación general. No se acredita la enumeración completa con los fragmentos seleccionados.

### q06 — ¿Cuál es el límite diario de los gastos de manutención de un autónomo en España cuando no hay pernocta?

Importe y fila España/sin pernocta vinculados al autónomo. En 480/64 el testigo explícito está en rango 6; las cifras de empleados en rangos anteriores no sustituyen su contexto.

### q07 — ¿Qué tipo general de IVA se aplica en 2025?

256/32: top-8 con índice/novedades pero sin el tipo general solicitado. 384/48 y 480/64: regla explícita en página 119.

### q08 — ¿Cuándo debo presentar el modelo 303 correspondiente al primer trimestre de 2025?

256/32 y 384/48 recuperan la regla general trimestral; 480/64 recupera plazos del régimen simplificado. La pregunta pide una fecha concreta de 2025: falta contrastar calendario/inhábiles para validar esa fecha. A conserva esta limitación de la referencia; no corrige el benchmark ni afirma otro vencimiento.

### q09 — ¿Qué libros registro debe llevar un sujeto pasivo del IVA en régimen general?

Los cuatro libros aparecen juntos en los testigos. En 256/32, page-hit a k=3 no equivale a lista completa; testigo en rango 7.

### q10 — ¿Cuándo hay que regularizar las deducciones por bienes de inversión en el IVA?

256/32 y 384/48 incluyen cuatro/nueve años y diferencia superior a diez puntos. En 480/64 falta la regla temporal general en el top-8, aunque aparecen procedimiento y casos especiales.

### q11 — ¿Qué bienes no tienen la consideración de bienes de inversión a efectos del IVA por razón de su valor?

256/32 y 480/64 incluyen inferior a 3.005,06. En 384/48, el fragmento de página 139 termina antes de la lista: top-8 sin el umbral de valor.

### q12 — ¿Qué ocurre con las cuotas soportadas en bienes o servicios utilizados exclusivamente en operaciones con derecho a deducción?

Los testigos dicen deducción íntegra para uso exclusivo en operaciones con derecho a deducir.

### q13 — ¿Cómo se determina el tramo de cotización que corresponde a una persona trabajadora autónoma según sus rendimientos netos en 2025?

Las tres aportan información del sistema, pero no se acredita de forma explícita toda la regla de previsión del promedio mensual señalada en la nota. 256/32 aporta una explicación alternativa IRPF de previsión anual; no se confunde con el desarrollo completo del artículo 308.

### q14 — ¿Cuántos tramos de cotización hay en total entre la tabla reducida y la tabla general en 2025?

256/32 y 384/48 mezclan tramos de años previos con una tabla 2025 incompleta. 480/64 contiene en rango 3 las tablas completas de 2025, permitiendo contar 3 + 12.

### q15 — ¿Cuál es la base mínima del tramo 1 de la tabla reducida para 2025?

Año, tabla reducida, tramo y base mínima presentes. 384/48 responde desde un documento alternativo, aunque falle document-hit.

### q16 — ¿Cuál es la base mínima del tramo 1 de la tabla general para 2025?

256/32 y 480/64 contienen la fila bajo 2025. En 384/48 la continuidad entre rangos 1 y 6 permite reconstruirla, pero el encabezado y la fila están separados: A, no S inequívoco.

### q17 — ¿Cuál es la base máxima de cotización aplicable a los autónomos en 2025?

256/32 y 384/48 recuperan la regla de base máxima RETA. En 480/64 la misma cifra aparece para artistas/taurinos: no se acepta extrapolarla al RETA.

### q18 — ¿Qué tipos de cotización por contingencias comunes, contingencias profesionales y MEI se establecen para los autónomos en 2025?

480/64 reúne los tres tipos en contexto RETA. 256/32 y 384/48 recuperan profesional/MEI, pero las coincidencias de 28,30 en otros contextos no se aceptan como prueba equivalente.

### q19 — ¿Qué porcentaje resulta de sumar los tipos de contingencias comunes, contingencias profesionales, MEI, cese de actividad y formación profesional previstos para el RETA en 2025?

Ningún top-8 reúne los cinco componentes en contexto correcto. El 0,10 adicional de página 16 no es la formación de página 30. Page-hit no fundamenta la suma.

### q20 — ¿Ha cambiado la base mínima del tramo 1 de la tabla reducida entre 2024 y 2025?

256/32 y 384/48 permiten comparar tabla reducida 2024 y 2025 con encabezados. 480/64 recupera 2025 y otros años/contextos, sin acreditar el dato 2024 solicitado.

### q21 — ¿Ha cambiado la base mínima del tramo 1 de la tabla general entre 2024 y 2025?

256/32 permite comparar las filas de 2024 y 2025. En 384/48 falta la fila general 2025; en 480/64 falta la fila 2024. La coincidencia numérica con 2023 no prueba ausencia de cambio.

### q22 — ¿Cuándo puede considerarse afecta una embarcación deportiva o de recreo a una actividad económica?

Regla general de exclusividad para embarcaciones presente en las tres; 480/64 la encuentra en rango 5, no en su primer acierto de página.

### q23 — ¿Cómo considera el IRPF las monedas virtuales o criptomonedas a efectos fiscales?

Consideración como bienes inmateriales presente; en 256/32 el primer page-hit es información sobre modelos, mientras la definición está en rango 6.

### q24 — ¿Cómo tributa un autónomo residente fiscal en Andorra que factura a clientes españoles?

Caso sin respuesta según benchmark. El primer resultado trata IVA/devoluciones o modelos, no resuelve residencia en Andorra. No se ha ejecutado un sistema de abstención ni auditado exhaustivamente todo el corpus.

### q25 — ¿Qué bonificación concreta existe para contratar a un familiar menor de edad para tareas domésticas?

Caso sin respuesta según benchmark. Bonificaciones de cuidadores, hogar o conciliación no prueban la bonificación exacta para contratar a un familiar menor en tareas domésticas.

### q26 — ¿Cuánto tendré que pagar exactamente de IVA este trimestre según mis facturas?

Caso personal: los primeros resultados tratan declaraciones informativas y sus plazos. No hay facturas del usuario para determinar una cuota exacta.

### q27 — ¿En qué tramo de cotización de autónomos me corresponde estar según mis ingresos?

Caso personal: aparecen cese de actividad o cotización de trabajadores del mar. Faltan datos del usuario y no se demuestra asignación correcta de tramo.

### q28 — Voy a darme de baja como autónomo a mitad de mes, ¿cuánto tendré que pagar exactamente ese mes?

Caso personal: los primeros resultados tratan bonificaciones o prestación por cese; no equivalen al cálculo de la cuota al darse de baja a mitad de mes.

### q29 — Si voy a facturar 45.000 euros y tengo 12.000 euros de gastos, ¿cuánto pagaré exactamente de IRPF?

Caso personal: límites de módulos y ejemplos de otros contribuyentes no calculan la cuota exacta del usuario. Ingresos menos gastos no basta para una liquidación final.

### q30 — ¿Qué tiempo va a hacer este fin de semana en Madrid?

Fuera de alcance: temporales pasados y eventos con Madrid son coincidencias temáticas, no una previsión meteorológica.

### q31 — ¿Puedes recomendarme un restaurante para una comida de negocios?

Fuera de alcance: epígrafes, dietas y gastos de restaurantes no son recomendaciones de restaurantes.

### q32 — ¿Qué tipo del Impuesto sobre Sociedades debo aplicar si constituyo una Sociedad Limitada?

Fuera de alcance según briefing/benchmark: deducciones IRPF por inversión en sociedades no determinan el tipo del Impuesto sobre Sociedades.

### q33 — Un cliente no me ha pagado una factura, ¿qué pasos legales puedo seguir para reclamar la deuda?

Fuera de alcance: IVA de créditos impagados o procedimientos de pago no constituyen una guía de reclamación jurídica de deudas.

### q34 — ¿Cómo se aplica la afectación parcial cuando un elemento patrimonial divisible se utiliza en parte para la actividad económica?

Parte realmente utilizada, aprovechamiento separado e independiente y exclusión de indivisibles presentes.

### q35 — ¿Cómo se calcula el IVA soportado deducible cuando un bien o servicio se utiliza parcialmente en operaciones con derecho a deducción?

Los testigos vinculan uso parcial en operaciones con derecho a deducir con porcentaje de prorrata general.

### q36 — ¿Qué diferencia debe existir entre los porcentajes de deducción para que proceda la regularización de un bien de inversión?

Diferencia superior a diez puntos presente. En 256/32 y 384/48 el testigo está en rango 4 y 5, respectivamente.

### q37 — ¿Cuáles son los tres tramos de la tabla reducida de cotización de autónomos en 2025?

Los tres intervalos de la tabla reducida aparecen bajo 2025 en las tres configuraciones.

### q38 — ¿Qué porcentaje de los ingresos de un autónomo debe proceder de un único cliente para que pueda ser considerado trabajador autónomo económicamente dependiente (TRADE)?

75 % e ingresos de un cliente vinculados al TRADE. Se citan testigos de LETA; puede haber evidencia alternativa anterior en IRPF. Los rangos no son mínimos certificados.

### q39 — ¿Cuántos días hábiles de interrupción anual de la actividad tiene un trabajador autónomo económicamente dependiente?

18 días hábiles y posibilidad de mejora contractual presentes en las tres.

### q40 — ¿En qué situaciones puede un trabajador autónomo económicamente dependiente contratar a un único trabajador por cuenta ajena?

Los cinco supuestos están presentes combinando 1+4 en 256/32 y en un fragmento en las otras dos. S acredita los supuestos preguntados, no todas las condiciones posteriores de contratación.

## Conclusión de la revisión

Las tres configuraciones presentan carencias distintas. El empate automático de
24/28 páginas a k=8 no equivale a igualdad de evidencia útil. Ejemplos comprobados:

- 256/32 y 384/48 conservan la regla temporal completa de q10; 480/64 no la reúne.
- 480/64 reúne la tabla de 2025 de q14 y los tres tipos de q18; las menores dejan contexto incompleto.
- 256/32 reúne los dos años de q21; las otras configuraciones no acreditan ambos.
- q04, q05, q13 y q19 no tienen suficiencia confirmada en ninguna configuración.
- q08 requiere validar el salto de regla general a fecha concreta; q16 en 384/48 exige reconstruir una tabla.

No se calcula una clasificación ganadora a partir de estas etiquetas asistidas:
son juicios con distinto grado de certeza, no un nuevo gold validado. El tamaño y
k se deben elegir conjuntamente con el presupuesto de contexto. A k=8, las medias
ya medidas son 1.944,0, 2.965,1 y 3.739,8 tokens respectivamente; incluyen overlap
pero no prompt/citas. Un chunk mayor no garantiza mayor suficiencia.

La revisión queda terminada como auditoría cualitativa de las 40 preguntas. La
validación humana de estos juicios, una selección final de parámetros y una prueba
de respuestas/abstención del pipeline son trabajos distintos; no se presentan
como completados. No es necesario añadir un parser complejo para cerrar esta fase.

## Casos especiales y threshold

Las diez preguntas especiales reciben resultados porque el experimento desactiva
el threshold. Se revisó su primer resultado en cada configuración y se conservaron
los scores de los ocho. Eso no demuestra que el pipeline responda mal o bien:
no se ha ejecutado el LLM ni sus decisiones de alcance o abstención.
El mismo número de resultados no equivale a respuestas fundamentadas.
No se selecciona un threshold a partir de esta muestra.

## Artefactos y reproducibilidad

- Matriz verificable: [retrieval_review_matrix.json](retrieval_review_matrix.json).
- Ejemplos detallados: [retrieval_evidence_review.md](retrieval_evidence_review.md).
- Métricas automáticas: [retrieval_evaluation.md](retrieval_evaluation.md).

Ejecución: `20261004T134946547175Z`. Los textos originales completos permanecen
 en `results.json` bajo la carpeta de evaluación del manifiesto. No se alteraron
 el benchmark, el corpus, los embeddings, el retriever ni los resultados de esa ejecución.

SHA-256 results.json: `b52ba84de1cbf6c9971b6108e5da0c4e0bb46d93c56497e6e05bf42428aebf04`.
