# Chunking de AsesorIA: tokens y procedencia

## Estado y decisiones

Entrada pública: `chunk_document`. Devuelve chunks con metadatos compartidos,
texto original, texto preparado para embeddings, posiciones de caracteres y
conteos. No genera embeddings ni guarda información en ChromaDB.

Se reutilizan `LoadedPage`, `ChunkMetadata` y `Settings`. No se usa
`RetrievedChunk` porque su score corresponde a la recuperación, no a la ingesta.
`page_end` ya está incorporado en el contrato de Javier.

La estrategia es estructural cuando recibimos secciones fiables o encabezados
Markdown explícitos, y recursiva dentro de cada sección. Sin estructura fiable,
se divide el texto disponible sin inventar títulos. No hay un parser específico
para AEAT/BOE ni un clasificador semántico de títulos.

## Dos medidas distintas

- Tokens: para decidir si cabe el texto completo que recibirá el modelo.
- Posiciones de caracteres: para localizar el contenido original y sus páginas.

Los offsets incluyen start y excluyen end. Cada `chunk.text` coincide con
`texto_unido[chunk.start:chunk.end]`. Se eliminan espacios exteriores ajustando
esas posiciones. Los separadores entre páginas no se asignan a ninguna página.

## Tokenizer y presupuesto

`load_tokenization(settings)` carga solo el tokenizer de `embedding_model`.
El algoritmo recibe ese objeto; no contiene el nombre de un modelo fijo.
Se pueden inyectar otros tokenizers mediante la misma interfaz.

`Tokenization.prepare` es el único lugar donde se construye el texto final:
prefijo del modelo + contexto de sección + contenido. El conteo incluye los
tokens especiales, no añade padding y nunca trunca. Se cuenta el texto completo,
no la suma de conteos aislados. Si un título consume el presupuesto se genera
un error explícito. Un carácter indivisible que no quepa también genera error.

Con el modelo provisional multilingual-e5-base se usa `passage: ` para documentos
y un límite de 512 tokens. Al cambiar de modelo hay que revisar tokenizer,
prefijo y límite. Para consultas, la futura capa de embeddings deberá usar el
formato de consulta del modelo (en E5, `query: `), no el de documentos.

El embedder deberá consumir `embedding_text` tal como se entrega, sin añadir
otra vez el título/prefijo ni truncar. Es imprescindible coordinar esta política
con el componente de indexación. Los tokens de padding de un lote no son parte
del presupuesto de contenido del chunk.

`ChunkingConfig` no tiene tamaño ni overlap ganadores por defecto. Candidatos:

| max_tokens total | overlap_tokens del contenido |
|---:|---:|
| 256 | 32 |
| 384 | 48 |
| 480 | 64 |

Son configuraciones experimentales. Ninguna se declara mejor por estas pruebas.
El límite configurado no puede superar el del modelo. Si el tokenizer no
declara un límite real, se exige `embedding_max_tokens` explícito.

## División y overlap

1. Se intenta conservar la sección completa si cabe con su contexto.
2. Si no cabe, se divide por párrafos, líneas y espacios, en ese orden.
3. Como último recurso se subdividen intervalos de caracteres; se aceptan
   únicamente cuando su texto preparado cabe en tokens. No se decodifican
   trozos de tokens para reconstruir el texto, preservando así su procedencia.
4. Se agrupan unidades contiguas contando cada candidato completo.
5. El siguiente chunk reutiliza unidades completas del sufijo anterior, hasta
   el objetivo de overlap, siempre que quede espacio para contenido nuevo.

El overlap puede ser menor o cero, especialmente si las unidades son grandes.
Se registra `Chunk.overlap_tokens` efectivo sobre el contenido compartido, sin
prefijo, título ni tokens especiales. No se solapan secciones diferentes.
`Chunk.token_count` sí incluye toda la entrada preparada y los tokens especiales.

## Secciones y limpieza

`SectionSpan` contiene start/end globales, section_label y section_path. Puede
aportarlo una etapa previa que haya identificado la sección de forma fiable.
Se rechazan secciones desordenadas, superpuestas o fuera del texto. Los huecos
se conservan y heredan los metadatos documentales, sin inventar un título nuevo.

Para Markdown se puede activar `detect_markdown_headings=True`. Reconoce títulos
ATX (`#`, `##`, etc.), construye rutas jerárquicas e ignora bloques de código
cercados. No interpreta tablas, HTML ni toda la sintaxis Markdown. No activar
esa opción indiscriminadamente sobre texto extraído de PDF.

La detección visual de títulos PDF queda pendiente. Los encabezados proporcionados
por la detección Markdown siguen dentro del contenido original; al añadir contexto
puede repetirse el título en el primer chunk. También se cuenta esa repetición.

Las páginas deben proceder del mismo documento, estar ordenadas y numeradas
positivamente. Hay que preparar el texto ANTES de calcular sus posiciones.
Si se usa la limpieza de Javier que elimina saltos de línea, los títulos deben
identificarse/conservarse antes y recalcular sus posiciones sobre el texto final.
No pasar secciones calculadas antes de una limpieza que altera caracteres.
El chunker no aplica esa limpieza ni llama al cargador por su cuenta.

## Metadatos

Cada resultado contiene una instancia independiente de `ChunkMetadata`.
Se copian todos los campos documentales, incluidos vigencia y session_id.
Se calculan page, page_end y chunk_index (desde cero, global por documento), y
se asignan las etiquetas de sección fiables. Una sola página produce page_end=page.
Los documentos privados requieren session_id. El aislamiento en las consultas
posteriores sigue siendo responsabilidad del vector store/retriever.

El texto original debe utilizarse para citas. `embedding_text` lleva contexto
añadido, que no debe presentarse como si fuera una cita literal del documento.
El rango de páginas corresponde al cuerpo original del chunk, no al título
añadido desde otra página.

## Ejemplo mínimo

```python
from src.common.schemas import ChunkMetadata
from src.common.settings import get_settings
from src.common.tokenization import load_tokenization
from src.ingestion.loaders import LoadedPage
from src.ingestion.chunking import ChunkingConfig, chunk_document

tokenization = load_tokenization(get_settings())
metadata = ChunkMetadata(
    doc_id="ejemplo", doc_type="official_guide", tax="IRPF",
    fiscal_year=2025, source_scope="public",
)
chunks = chunk_document(
    [LoadedPage("Texto de ejemplo de la página 7.", 7)],
    metadata,
    config=ChunkingConfig(max_tokens=256, overlap_tokens=32),  # Solo experimento.
    tokenization=tokenization,
)
for chunk in chunks:
    print(chunk.text, chunk.metadata.page, chunk.metadata.page_end, chunk.token_count)
```

También se puede utilizar `ChunkingConfig.from_settings(settings)` tras definir
CHUNK_SIZE_TOKENS y CHUNK_OVERLAP_TOKENS; si faltan, se solicita elegirlos.

## Entorno y pruebas con uv

Si no existe un entorno, crearlo con `uv venv`. No reemplazar un entorno existente
sin revisarlo. En Windows, para instalar en el entorno elegido:

```powershell
uv pip install --python .venv/Scripts/python.exe -r requirements.txt
.venv/Scripts/python.exe -m pytest tests/ -q
```

Las pruebas normales no descargan tokenizers. Usan un doble con tokens por byte
para distinguir tokens de caracteres; no representa la tokenización de E5.
Para ejecutar además las tres configuraciones con el tokenizer real de E5:

```powershell
$env:RUN_TOKENIZER_INTEGRATION = "1"
.venv/Scripts/python.exe -m pytest tests/test_chunking_tokenizer.py -q
```

Se descargan solo archivos del tokenizer. La primera ejecución requiere red.
Las pruebas verifican presupuestos completos, contenido, offsets, páginas,
metadatos, privacidad, títulos fiables y overlap. No miden la calidad semántica.

## Evaluación pendiente

Comparar las tres configuraciones con el mismo corpus, tokenizer/modelo y k,
usando preguntas cuyo contexto esté realmente indexado. Registrar configuración,
revisión del modelo/tokenizer, número de chunks, overlap efectivo y resultados
de recuperación (por ejemplo, hit@k/recall@k con relevancia anotada).
Separar las preguntas con fuentes ausentes. No elegir por número de pruebas
superadas: esas pruebas comprueban corrección del código, no calidad de retrieval.

Referencias:
- https://huggingface.co/intfloat/multilingual-e5-base
- https://huggingface.co/docs/transformers/main_classes/tokenizer
