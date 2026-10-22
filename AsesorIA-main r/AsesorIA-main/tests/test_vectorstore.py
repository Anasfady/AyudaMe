"""Pruebas locales de Chroma con vectores simulados: no descargan modelos."""
import json
import os
import subprocess
import sys
from pathlib import Path
from unittest.mock import Mock

import chromadb
import pytest
from langchain_core.documents import Document

from src.common.schemas import ChunkMetadata
from src.common.settings import Settings
from src.indexing.embeddings import EmbeddingService
from src.indexing.vectorstore import get_vectorstore, add_documents_to_vectorstore
from src.ingestion.chunking import Chunk


def make_chunk(doc_id='doc', text='Texto original fiscal', prepared='passage: Contexto fiscal', **metadata):
    fields = dict(doc_id=doc_id, doc_type='official_guide', source_scope='public',
                  page=7, page_end=8, source_url='https://example.test/manual',
                  section_label='Deducciones', section_path='IVA > Deducciones')
    fields.update(metadata)
    return Chunk(text, prepared, ChunkMetadata(**fields), 0, len(text), 10, 0)


@pytest.fixture
def service():
    service = Mock(spec=EmbeddingService)
    service.embed_documents.side_effect = lambda texts: [[1.0, 0.0] for _ in texts]
    service.embed_query.return_value = [1.0, 0.0]
    return service


@pytest.fixture
def store(tmp_path, service):
    return get_vectorstore(Settings(_env_file=None, chroma_dir=str(tmp_path / 'db'),
                                    chroma_collection='test_chunks'), embedding_service=service)


def test_separate_texts_metadata_cosine_and_no_automatic_embeddings(store, service):
    chunk = make_chunk()
    ids = add_documents_to_vectorstore([chunk], vectorstore=store)
    service.embed_documents.assert_called_once_with([chunk.embedding_text])
    result = store.collection.get(ids=ids, include=['documents', 'metadatas', 'embeddings'])
    assert result['documents'] == [chunk.text]
    assert result['metadatas'] == [chunk.metadata.to_store_dict()]
    assert result['metadatas'][0]['page_end'] == 8
    assert 'session_id' not in result['metadatas'][0]
    assert 'embedding_text' not in result['metadatas'][0]
    assert store.collection.configuration['hnsw']['space'] == 'cosine'
    assert result['embeddings'][0].tolist() == [1, 0]
    # With no embedding function, raw text cannot trigger automatic embeddings.
    with pytest.raises(ValueError):
        store.collection.query(query_texts=['no automatic embeddings'])


def test_idempotent_reindex_and_duplicate_batch(store):
    chunk = make_chunk()
    first = store.add_chunks([chunk, chunk])
    assert first[0] == first[1]
    assert store.add_chunks([chunk]) == [first[0]]
    assert store.collection.count() == 1


def test_ids_include_scope_and_session(store):
    ids = store.add_chunks([make_chunk(), make_chunk(source_scope='private', session_id='a'),
                            make_chunk(source_scope='private', session_id='b')])
    assert len(set(ids)) == 3
    assert store.collection.get(ids=[ids[1]])['metadatas'][0]['session_id'] == 'a'


def test_reject_private_without_session_before_embedding(store, service):
    with pytest.raises(ValueError, match='session_id'):
        store.add_chunks([make_chunk(), make_chunk(source_scope='private')])
    service.embed_documents.assert_not_called()
    assert store.collection.count() == 0


def test_empty_indexing_and_query(store, service):
    assert store.add_chunks([]) == []
    assert store.query([1, 0], top_k=4)['documents'] == [[]]
    service.embed_documents.assert_not_called()


def test_reject_document_without_prepared_text(store):
    with pytest.raises(TypeError, match='Chunk'):
        store.add_chunks([Document(page_content='Solo texto original')])


def test_existing_wrong_metric_is_not_silently_reused(tmp_path):
    path = str(tmp_path / 'wrong_metric')
    client = chromadb.PersistentClient(path=path, settings=chromadb.config.Settings(anonymized_telemetry=False))
    collection = client.create_collection('wrong_metric', embedding_function=None,
                                          configuration={'hnsw': {'space': 'l2'}})
    with pytest.raises(ValueError, match='cosine'):
        get_vectorstore(Settings(_env_file=None, chroma_dir=path, chroma_collection='wrong_metric'))
    assert collection.configuration['hnsw']['space'] == 'l2'


def test_cosine_distance_and_precomputed_query(store, service):
    service.embed_documents.return_value = None
    service.embed_documents.side_effect = lambda texts: [[1, 0], [0, 1], [-1, 0]]
    store.add_chunks([make_chunk(str(i)) for i in range(3)])
    result = store.query([1, 0], top_k=10)
    assert result['distances'][0] == pytest.approx([0, 1, 2])
    service.embed_query.assert_not_called()  # Store never embeds the query itself.


def test_persistence_after_writer_process_exits(tmp_path):
    path = str(tmp_path / 'persistent')
    script = '''
import json, sys
from types import SimpleNamespace
from src.common.settings import Settings
from src.indexing.vectorstore import get_vectorstore
from tests.test_vectorstore import make_chunk
settings = Settings(_env_file=None, chroma_dir=sys.argv[1], chroma_collection='persistent_test')
fake = SimpleNamespace(embed_documents=lambda texts: [[1.0, 0.0] for _ in texts])
store = get_vectorstore(settings, embedding_service=fake)
if sys.argv[2] == 'write':
    store.add_chunks([make_chunk()])
else:
    result = store.query([1.0, 0.0], top_k=4)
    print(json.dumps(result['documents']))
    assert result['metadatas'][0][0]['page_end'] == 8
    assert store.collection.configuration['hnsw']['space'] == 'cosine'
'''
    env = dict(os.environ, HF_HUB_OFFLINE='1', TRANSFORMERS_OFFLINE='1', PYTHONDONTWRITEBYTECODE='1')
    root = Path(__file__).resolve().parents[1]
    for mode in ('write', 'read'):
        result = subprocess.run([sys.executable, '-c', script, path, mode], cwd=root, env=env,
                                capture_output=True, text=True, timeout=90)
        assert result.returncode == 0, result.stdout + result.stderr
    assert json.loads(result.stdout.strip()) == [['Texto original fiscal']]



def test_respects_chroma_batch_limit(store, service, monkeypatch):
    monkeypatch.setattr(store.client, 'get_max_batch_size', lambda: 2)
    store.add_chunks([make_chunk(str(i)) for i in range(5)])
    assert [len(call.args[0]) for call in service.embed_documents.call_args_list] == [2, 2, 1]
    assert store.collection.count() == 5


def test_reopening_store_uses_same_collection(store):
    store.add_chunks([make_chunk()])
    reopened = get_vectorstore(store._settings)
    assert reopened.collection.count() == 1
    assert reopened._embedding_service is None
    assert reopened.query([1, 0], top_k=1)['documents'][0] == ['Texto original fiscal']
