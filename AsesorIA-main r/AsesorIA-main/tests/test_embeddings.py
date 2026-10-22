from types import SimpleNamespace
from unittest.mock import Mock
import numpy as np
import pytest

from src.common.settings import Settings
from src.indexing.embeddings import EmbeddingService, get_embedding_service


class FakeTokenizer:
    model_max_length = 512

    def encode(self, text, *, add_special_tokens, truncation):
        assert add_special_tokens and not truncation
        return list(range(len(text.split()) + 2))


@pytest.fixture
def model():
    return SimpleNamespace(tokenizer=FakeTokenizer(), max_seq_length=512,
                           encode=Mock(side_effect=lambda texts, **kwargs:
                                       np.array([[0.6, 0.8] for _ in texts])))


@pytest.fixture
def service(model):
    return EmbeddingService(Settings(_env_file=None), model=model, batch_size=2)


def test_documents_preserve_prepared_text_order_and_options(service, model):
    texts = ['passage: IVA > Deducciones\n\nContenido', 'passage: Otro fragmento']
    assert service.embed_documents(texts) == [[0.6, 0.8], [0.6, 0.8]]
    model.encode.assert_called_once_with(texts, batch_size=2, normalize_embeddings=True,
                                        convert_to_numpy=True, show_progress_bar=False, prompt='')


def test_chunks_use_embedding_text_only(service, model):
    chunk = SimpleNamespace(text='NO UTILIZAR', embedding_text='passage: Preparado')
    service.embed_chunks([chunk])
    assert model.encode.call_args.args[0] == ['passage: Preparado']


def test_query_prefix_normalization_and_reuse(service, model):
    assert service.embed_query('  ¿Qué gastos puedo deducir?  ') == [0.6, 0.8]
    assert model.encode.call_args.args[0] == ['query: ¿Qué gastos puedo deducir?']
    assert model.encode.call_args.kwargs['normalize_embeddings'] is True
    service.embed_documents(['passage: Documento'])
    assert model.encode.call_count == 2


@pytest.mark.parametrize('texts, error', [([], ValueError), ([''], ValueError),
    (['   '], ValueError), (['correcto', ''], ValueError), ([42], TypeError),
    ('texto', TypeError), (b'texto', TypeError)])
def test_invalid_documents_fail_before_encoding(service, model, texts, error):
    with pytest.raises(error):
        service.embed_documents(texts)
    model.encode.assert_not_called()


@pytest.mark.parametrize('query,error', [('', ValueError), (' \n', ValueError), (None, TypeError)])
def test_invalid_query(service, model, query, error):
    with pytest.raises(error):
        service.embed_query(query)
    model.encode.assert_not_called()


def test_empty_chunks(service):
    with pytest.raises(ValueError, match='vacío'):
        service.embed_chunks([])


@pytest.mark.parametrize('batch_size', [0, -1, True, 1.5])
def test_invalid_batch_size(model, batch_size):
    with pytest.raises(ValueError, match='batch_size'):
        EmbeddingService(model=model, batch_size=batch_size)


@pytest.mark.parametrize('configured,model_limit,expected', [(5, 512, 5), (512, 5, 5), (None, 5, 5)])
def test_length_limit_prevents_silent_truncation(model, configured, model_limit, expected):
    model.max_seq_length = model_limit
    service = EmbeddingService(Settings(_env_file=None, embedding_max_tokens=configured), model=model)
    service.embed_documents(['a b c'])  # Exactly five tokens including special tokens.
    model.encode.reset_mock()
    with pytest.raises(ValueError, match='no se truncará'):
        service.embed_documents(['a b c d'])
    with pytest.raises(ValueError, match='no se truncará'):
        service.embed_query('a b c')  # Prefix also consumes a token.
    model.encode.assert_not_called()


def test_loader_uses_configured_model_once(monkeypatch, model):
    import sentence_transformers
    factory = Mock(return_value=model)
    monkeypatch.setattr(sentence_transformers, 'SentenceTransformer', factory)
    service = EmbeddingService(Settings(_env_file=None, embedding_model='configured-model'))
    service.embed_query('Consulta')
    service.embed_documents(['passage: Documento'])
    factory.assert_called_once_with('configured-model')


def test_shared_service_cache(monkeypatch):
    import src.indexing.embeddings as module
    factory = Mock()
    monkeypatch.setattr(module, 'EmbeddingService', factory)
    get_embedding_service.cache_clear()
    try:
        assert get_embedding_service() is get_embedding_service()
        factory.assert_called_once_with()
    finally:
        get_embedding_service.cache_clear()
