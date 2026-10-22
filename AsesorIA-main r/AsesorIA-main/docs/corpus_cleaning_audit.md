# Auditoría de limpieza del corpus local

Ejecutar `python -m scripts.audit_corpus_cleaning` desde la raíz del proyecto.
El informe detallado queda en `chroma_db/cleaning_audit.json`, fuera de Git, con
hashes de los PDF, líneas eliminadas, frecuencias y ejemplos de páginas.

Se revisaron los siete PDF, 2.847 páginas, con remove_repeated_lines en su
configuración actual (min_ratio=0.5), sin modificar las funciones de ingesta.

| Documento | Apariciones eliminadas | Contenido eliminado |
|---|---:|---|
| IRPF parte 1 | 0 | Ninguno |
| IRPF parte 2 | 2396 | Viñetas • |
| IVA | 561 | Viñetas • |
| LGSS | 821 | Cabeceras BOE, legislación consolidada y Página N |
| LETA | 116 | Cabeceras BOE, legislación consolidada y Página N |
| RDL cotización | 192 | Cabecera BOE, CVE y línea de verificación |
| Orden cotización | 113 | Cabeceras BOE, legislación consolidada y Página N |

Se comprobó el conjunto completo de líneas retiradas, no solo las ocho primeras
mostradas en consola. Ninguna página con texto quedó vacía tras deduplicar ni
tras aplicar clean_text por separado. La numeración de páginas se conserva.
Esto NO certifica ausencia de todos los errores de extracción o limpieza.

## Política inicial propuesta para la evaluación

- Manuales AEAT (IRPF partes 1/2 e IVA): solo clean_text, preservando viñetas.
- Cuatro documentos RETA: remove_repeated_lines seguido de clean_text, pues los
  patrones retirados en estos archivos corresponden a cabeceras/pies revisados.
- Registrar esta política por documento y mantenerla idéntica en las tres
  configuraciones de chunking. No cambiarla en mitad de una comparación.
- Si cambia el hash de un PDF, repetir la auditoría: este resultado no autoriza
  a aplicar ciegamente la misma política a documentos futuros.

## Limitaciones

La función basada en frecuencia no identifica semánticamente cabeceras o pies.
En los manuales AEAT no retiró cabeceras/pies: o bien no alcanzan la frecuencia
requerida, o bien cambian entre páginas. Quedará ruido en la primera evaluación.
Los resultados no prueban que todos los pies hayan sido eliminados en RETA.
clean_text también cambia espacios y une palabras con guion al final de línea;
la fidelidad semántica y la extracción de tablas aún requieren revisión al examinar
los fragmentos recuperados. No se modificó el código de Javier.

Siguiente paso: implementar la indexación reproducible del corpus con esta política,
una colección por configuración y un registro de documentos, parámetros y conteos.
No se ha indexado el corpus completo ni ejecutado métricas en esta auditoría.
