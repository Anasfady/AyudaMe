# Vector store y retriever: contrato técnico

## Requisitos de integración

- Chroma persistente, búsqueda por vectores, top-k y umbral configurables.
- `retriever.invoke(question)` devuelve `list[langchain_core.documents.Document]`.
- `page_content` es el texto original, con metadatos de trazabilidad y páginas.
- Filtrado por metadatos. Los filtros funcionales NO equivalen a autorización.

La rama incorpora el pipeline de Helen desde main (PR #22). Se comprueba la
conexión real entre Chroma, nuestro retriever y RAGPipeline con embeddings y LLM
simulados, sin modificar el código del pipeline. Su anotación VectorStoreRetriever
es más restrictiva que el contrato que usa en ejecución: invoke(question).
Propuesta pendiente: ampliar esa anotación a Runnable[str, list[Document]].

## Decisiones del equipo y arquitectura implementada

```text
Chunk.embedding_text -> EmbeddingService.embed_documents -> vector
Chunk.text           ------------------------------------> documento en Chroma
Chunk.metadata.to_store_dict() --------------------------> metadatos en Chroma

question -> EmbeddingService.embed_query -> vector -> Chroma.query
         -> filtro de similitud -> Document(texto original, metadatos)
```

Usamos Chroma nativo, equivalente permitido por la recomendación de integración.
`embedding_function=None` y vectores explícitos evitan que Chroma genere un segundo
embedding desde el texto original. Sentence Transformers sigue siendo responsabilidad
de EmbeddingService. El retriever no añade `query:`: lo hace ese servicio una sola vez.

El título y `passage:` sirven a la representación semántica, pero no deben presentarse
como texto literal de la fuente. Solo `Chunk.text` se almacena como documento y se cita.
No se almacena embedding_text como documento ni como un nuevo campo de metadatos.

## Interfaces públicas

```python
from src.indexing.embeddings import EmbeddingService
from src.indexing.vectorstore import get_vectorstore, add_documents_to_vectorstore
from src.retrieval.retriever import get_retriever

# Abrir no carga el modelo: el servicio puede inyectarse o crearse bajo demanda.
store = get_vectorstore(settings, embedding_service=EmbeddingService(settings))
ids = add_documents_to_vectorstore(chunks, vectorstore=store)
retriever = get_retriever(top_k=8, score_threshold=0.82,
                          filter_dict={'tax': 'IVA'}, vectorstore=store)
documents = retriever.invoke('¿Qué gastos puedo deducir?')
```

Con el pipeline integrado, la conexión es:

```python
from src.rag.pipeline import RAGPipeline

pipeline = RAGPipeline(retriever=retriever, llm=mi_llm)
resultado = pipeline.answer_query('¿Qué gastos puedo deducir?')
```

El ejemplo presupone un LLM ya configurado. La respuesta contiene answer y
source_documents. Si no hay documentos, el pipeline sigue invocando al LLM;
el umbral por sí solo no garantiza abstención.
`add_documents_to_vectorstore` recibe Chunk, no Document: cambiarlo a Document
eliminaría la distinción entre texto preparado y texto original.
`store.add_chunks(chunks)` es equivalente. Devuelve IDs en orden; una entrada vacía
produce `[]`. La búsqueda de infraestructura `store.query(vector, top_k=..., filter_dict=...)`
recibe vectores y devuelve resultados nativos con distancias. No debe exponerse como
endpoint público: no implementa autorización.

## Metadatos y compatibilidad

Se reutiliza ChunkMetadata y `to_store_dict()`; se omite None como prevé el contrato.
Se conservan doc_id, tax, doc_type, fiscal_year, valid_from, valid_to, section_label,
section_path, page, page_end, source_url, retrieved_at, source_scope, session_id
cuando existe, y chunk_index. No se inventa un campo `section` en el schema.

El schema actual NO tiene `source`. Solo en los Document de salida se añade el alias
`source = source_url or doc_id`, manteniendo ambos campos originales. Este es el
adaptador explícito al contrato de Helen: format_docs muestra ese valor junto
con page/page_end y el texto original; esta conexión está probada. Los filtros usan los campos
almacenados (por ejemplo source_url), no este alias calculado al recuperar.

## Persistencia, métrica e IDs

PersistentClient escribe en `settings.chroma_dir`, colección `settings.chroma_collection`.
No requiere persist() manual. Las pruebas cierran un proceso escritor y recuperan
los datos desde otro proceso lector. La aplicación debe reutilizar el store durante
su vida; la finalización del proceso libera los recursos de Chroma.

Se crea explícitamente `configuration={'hnsw': {'space': 'cosine'}}`. Al reabrir
se comprueba la configuración efectiva: una colección existente con l2 produce un
error, sin migrarla ni borrarla. Se requiere Chroma >=1.5.9,<2 (API probada localmente)
y se declara langchain-core como dependencia directa.

Los IDs son SHA-256 deterministas de ámbito, sesión, doc_id, chunk_index, posiciones,
texto original y texto preparado. Upsert evita duplicados al reindexar exactamente
los mismos chunks, incluso si están repetidos dentro del lote. No incluye retrieved_at:
una nueva fecha de ingesta actualiza los metadatos del mismo chunk. Se divide la carga
según el máximo de lote de Chroma. No hay transacción global entre múltiples lotes.

Cambiar el texto o la estrategia genera nuevos IDs: NO se eliminan versiones anteriores
automáticamente. Para comparar configuraciones, usar colecciones distintas. Una colección
debe contener vectores del mismo modelo y convención: Chroma valida la dimensión, pero
no puede detectar modelos distintos con igual dimensión. No se implementa migración
ni un registro de versiones de modelos en esta primera capa.

## Parámetros provisionales y semántica

- top_k=8 es el default inicial V1; se devuelven como máximo k resultados.
- score_threshold=0.82 es el default inicial V1 (similitud cosine); None desactiva el umbral. Véase `docs/v1_retrieval_configuration.md` para alcance y límites.
- Chroma devuelve distancia cosine: `d = 1 - cosine_similarity`.
- Aplicamos `similarity = 1 - d` y conservamos `similarity >= score_threshold`.
- El umbral admite [-1,1]. NO representa una probabilidad ni un relevance score
  transformado a [0,1] de LangChain. Los vectores opuestos pueden dar similitud negativa.
- Primero Chroma filtra metadatos y busca hasta k candidatos; después se aplica el
  umbral. El resultado puede tener menos de k elementos o estar vacío.
- La búsqueda HNSW es aproximada. Las pruebas técnicas no certifican calidad fiscal.

## Filtros y privacidad por instancia

get_retriever(..., session_id=None) devuelve solo documentos públicos.
Con session_id='A', devuelve públicos y privados con session_id exactamente 'A'.
El backend debe validar la sesión antes de construir el retriever y asignar esa
misma identidad correctamente a los documentos privados durante la ingesta.
Esta capa comprueba el tipo y rechaza cadenas vacías; no autentica usuarios.
No normaliza ni recorta identificadores: la comparación es exacta.

```python
retriever = get_retriever(vectorstore=store, session_id=session_validada)
pipeline = RAGPipeline(retriever=retriever, llm=mi_llm)
resultado = pipeline.answer_query('Mi pregunta')
```

RAGPipeline y invoke(question) permanecen intactos. Cada instancia conserva su
sesión; la propiedad pública session_id no tiene setter. Crear una instancia nueva
para otra sesión. No compartir el retriever ni el pipeline que lo contiene entre
sesiones. Sí se puede compartir el vectorstore y el servicio de embeddings.
La propiedad de solo lectura previene cambios accidentales: no es una barrera
contra código de backend con acceso a los atributos internos de Python.

El filtro obligatorio es public OR (private AND session_id autorizado).
filter_dict admite la sintaxis nativa de Chroma y se combina mediante AND con
ese filtro obligatorio. Se valida y copia: solo puede reducir el acceso, nunca
ampliarlo, aunque contenga $or o solicite otra sesión. Se aplica antes del top-k.
Además, se revisa la autorización de los metadatos devueltos: privados sin sesión,
registros de otras sesiones y ámbitos desconocidos se descartan.
RunnableConfig y kwargs de invoke no cambian la sesión autorizada.

La aplicación debe proporcionar la sesión validada al construir el retriever;
no debe tomar un identificador arbitrario del cliente como autorización. Este es
el punto de integración pendiente en la aplicación, no un cambio del pipeline.
Las pruebas usan Chroma temporal, vectores y LLM simulados para comprobar sesiones
A/B, acceso público, filtros adversos y la conexión con el pipeline real.

Chroma local no es una barrera frente a quien tenga acceso directo a sus archivos o
al cliente de infraestructura. La carpeta predeterminada chroma_db está excluida de Git;
si se configura otra carpeta hay que mantenerla fuera del repositorio.

## Pruebas y límites del alcance

```powershell
python -m pytest tests/test_vectorstore.py tests/test_retriever.py -q
python -m pytest tests/ -q
```

Los tests usan Chroma temporal real y EmbeddingService simulado: no descargan ni ejecutan
E5. Comprueban textos, vectores explícitos, metadatos, persistencia entre procesos,
cosine, IDs, lotes, top-k, filtros, umbral y contrato Runnable/Document. Además,
se prueba la conexión con RAGPipeline mediante un LLM simulado. No implementan
Hit@k, Recall@k, calibración, benchmark fiscal, generación LLM ni cambios de prompts.

Referencias de API:
- https://docs.trychroma.com/docs/collections/configure
- https://docs.trychroma.com/docs/querying-collections/metadata-filtering
