# Capa de embeddings

`src/indexing/embeddings.py` transforma texto en vectores con sentence-transformers.
No almacena vectores ni realiza búsquedas.

## Contrato

- `EmbeddingService(settings=None, model=None, batch_size=32)` carga una vez el
  modelo configurado. `model` permite inyectar un modelo para pruebas. El tamaño
  de lote controla memoria y rendimiento, no el tamaño de los chunks.
- `embed_documents(embedding_texts)` recibe textos ya preparados y devuelve una
  lista de vectores en el mismo orden. No añade ni elimina prefijos o contexto.
- `embed_chunks(chunks)` adapta los chunks usando exclusivamente `embedding_text`.
- `embed_query(query)` recibe una pregunta sin preparar, recorta espacios exteriores
  y añade `query: `. No pasar consultas que ya tengan el prefijo de preparación.
- `get_embedding_service()` reutiliza una instancia por proceso. En una aplicación
  con varios procesos cada uno tendrá su modelo. Reiniciar al cambiar configuración.

Ambas rutas solicitan normalización L2 y devuelven listas de números Python.
Los textos vacíos y lotes vacíos producen errores. Se comprueba la longitud con
el tokenizer del modelo, incluyendo prefijo y tokens especiales, antes de inferir.
El límite efectivo es el menor entre `max_seq_length` del ejecutor y el límite
configurado si existe. Los excesos producen un error, nunca truncamiento silencioso.
La validación de longitud no modifica la estrategia ni la interfaz de chunking.

```python
from src.indexing.embeddings import get_embedding_service

service = get_embedding_service()
# chunks procede de chunk_document(...)
vectors = service.embed_chunks(chunks)
question_vector = service.embed_query('¿Qué gastos puedo deducir?')
```

E5 es la opción provisional actual. Si se cambia el modelo, revisar las convenciones
para consultas y documentos; el prefijo de consulta implementado aquí es el de E5.
Se usa `encode(..., prompt="", normalize_embeddings=True)` para impedir que un
prompt por defecto del modelo duplique los prefijos ya preparados.

## Dependencias y pruebas

Se añade `sentence-transformers>=3.4,<4`, compatible con el rango actual
`transformers>=4.45,<5`. El entorno de pruebas se instala con uv a partir de
requirements.txt; esto no migra el proyecto a uv.lock ni modifica su .venv existente.

Pruebas ordinarias, sin descargar pesos:

```powershell
python -m pytest tests/test_embeddings.py -q
python -m pytest tests/ -q
```

Integración real opcional (descarga pesos E5 en la caché local y ejecuta en CPU):

```powershell
$env:RUN_EMBEDDINGS_INTEGRATION='1'
python -m pytest tests/test_embeddings_integration.py -q
Remove-Item Env:RUN_EMBEDDINGS_INTEGRATION
```

La integración comprueba conexión con chunking, dimensiones, valores finitos,
normalización y equivalencia con llamadas directas al modelo. No evalúa retrieval.
El CI normal la omite y los tests unitarios inyectan un modelo simulado.

Referencias:
- https://huggingface.co/intfloat/multilingual-e5-base
- https://www.sbert.net/docs/package_reference/sentence_transformer/SentenceTransformer.html
