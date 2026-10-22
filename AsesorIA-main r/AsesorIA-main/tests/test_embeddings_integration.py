"""Opt-in: RUN_EMBEDDINGS_INTEGRATION=1 descarga pesos reales de E5."""
import os
import numpy as np
import pytest

from src.common.schemas import ChunkMetadata
from src.common.settings import Settings
from src.common.tokenization import Tokenization
from src.ingestion.chunking import ChunkingConfig, chunk_document
from src.ingestion.loaders import LoadedPage
from src.indexing.embeddings import EmbeddingService

pytestmark = pytest.mark.skipif(
    os.environ.get('RUN_EMBEDDINGS_INTEGRATION') != '1',
    reason='Activa RUN_EMBEDDINGS_INTEGRATION=1 para descargar y ejecutar E5',
)


def test_real_e5_chunking_documents_and_query():
    from sentence_transformers import SentenceTransformer
    model = SentenceTransformer('intfloat/multilingual-e5-base', device='cpu')
    service = EmbeddingService(Settings(_env_file=None), model=model, batch_size=1)
    tokenization = Tokenization(model.tokenizer, model.max_seq_length, 'passage: ')
    chunks = chunk_document(
        [LoadedPage('Los gastos deducibles requieren justificación documental. ' * 30, 1)],
        ChunkMetadata(doc_id='synthetic', doc_type='official_guide', source_scope='public'),
        config=ChunkingConfig(256, 32), tokenization=tokenization,
    )
    documents = np.asarray(service.embed_chunks(chunks))
    query = np.asarray(service.embed_query('¿Cómo justifico mis gastos?'))
    assert documents.shape == (len(chunks), 768)
    assert query.shape == (768,)
    assert np.isfinite(documents).all() and np.isfinite(query).all()
    np.testing.assert_allclose(np.linalg.norm(documents, axis=1), 1, atol=1e-5)
    np.testing.assert_allclose(np.linalg.norm(query), 1, atol=1e-5)
    expected = model.encode([c.embedding_text for c in chunks], prompt='', normalize_embeddings=True)
    np.testing.assert_allclose(documents, expected, atol=1e-5)
    expected_query = model.encode(['query: ¿Cómo justifico mis gastos?'], prompt='', normalize_embeddings=True)[0]
    np.testing.assert_allclose(query, expected_query, atol=1e-5)
