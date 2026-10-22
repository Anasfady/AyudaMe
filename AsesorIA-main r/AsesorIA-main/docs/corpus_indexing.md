# Indexación experimental del corpus

El script `python -m scripts.index_corpus` comprueba el catálogo y valida el
chunking de los siete PDF sin generar embeddings. Las candidatas son 256/32,
384/48 y 480/64; no hay una ganadora validada.

`python -m scripts.index_corpus --index` realiza además la indexación completa.
Puede consumir bastante tiempo en CPU. Carga un único EmbeddingService, utiliza
lotes de 128 chunks para dar progreso y conserva el batching interno del modelo.
No modifica los servicios compartidos ni sus contratos.

Cada ejecución crea una carpeta nueva bajo `<settings.chroma_dir>/corpus_runs/`
y las colecciones `corpus_256_32`, `corpus_384_48` y `corpus_480_64`. Esta separación
experimental evita mezclar configuraciones o documentos de ejecuciones antiguas;
no cambia la colección de producción configurada. Repetir la orden crea otro
experimento, no reanuda el anterior. No hay eliminación automática de datos.

Se utiliza el tokenizer del modelo configurado. Los vectores se calculan desde
`Chunk.embedding_text`, mientras Chroma conserva `Chunk.text` y sus metadatos.
El texto original aquí significa el texto tras la limpieza acordada: clean_text
para los manuales AEAT; remove_repeated_lines seguido de clean_text para RETA.
No se infieren títulos de PDF. Los límites incluyen prefijo y tokens especiales.

Un manifiesto local registra modelo, hashes de PDFs, parámetros, recuentos,
huellas de texto/metadatos e IDs. Los estados son in_progress, indexed y verified.
Una interrupción deja una ejecución incompleta, que no debe usarse para evaluar.
Al finalizar se abre un proceso nuevo para comprobar recuentos, texto, metadata,
dimensiones, normalización, métrica cosine (validada por VectorStore) y búsqueda
por vector. La pregunta de comprobación no mide calidad del retrieval.

Puede repetirse esa comprobación sin cargar E5:
`python -m scripts.index_corpus --verify RUTA_AL_MANIFIESTO`

Para trabajar sin red con los archivos de modelo ya cacheados, en Git Bash:
`HF_HUB_OFFLINE=1 python -m scripts.index_corpus --index`.

Estas son decisiones de organización de experimentos del equipo, no requisitos
del briefing. Los requisitos de trazabilidad se mantienen mediante los contratos
compartidos. Hit@k, calibración de threshold y elección de tamaños quedan para
la evaluación posterior. Los datos generados permanecen fuera de Git.

## Ruta de persistencia en Windows

En la instalación comprobada (Chroma 1.5.9), una ruta con caracteres no ASCII,
como `Módulo`, no guarda los binarios HNSW al superar el umbral de persistencia.
Los upserts pueden devolver éxito y la reapertura fallar. Se reprodujo con 1100
vectores simulados; en una ruta ASCII la misma prueba pasó. Por eso el script
rechaza esas rutas en Windows antes de cargar E5. No hay que renombrar el repo:
configura CHROMA_DIR con una carpeta de datos sin acentos, por ejemplo
`C:/Users/gemac/AsesorIA-data/chroma_db`. Mantén esa configuración al evaluar.
Esta es una limitación observada de la instalación, no una regla general sobre
nombres de archivos de Python. Las ejecuciones fallidas no deben usarse para evaluar.
