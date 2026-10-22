"""Pruebas de la orquestación del corpus sin descargar E5."""
import json
import subprocess
import sys
from unittest.mock import Mock

import pytest

from scripts.index_corpus import index_chunks, save_manifest, verify_saved
from src.common.schemas import ChunkMetadata
from src.common.settings import PROJECT_ROOT, Settings
from src.indexing.vectorstore import get_vectorstore
from src.ingestion.chunking import Chunk


def test_batches_preserve_text_and_reopen_in_new_process(tmp_path):
    service = Mock()
    service.embed_documents.side_effect = lambda texts: [[1.0, 0.0] for _ in texts]
    store = get_vectorstore(Settings(_env_file=None, chroma_dir=str(tmp_path),
                                    chroma_collection="corpus_test"), embedding_service=service)
    chunks = [Chunk(f"original {i}", f"passage: contexto {i}",
                    ChunkMetadata(doc_id="doc", doc_type="law", source_scope="public",
                                  page=1, page_end=2, chunk_index=i), 0, 10, 12, 0)
              for i in range(3)]
    records = index_chunks(store, chunks, batch_size=2)
    assert [call.args[0] for call in service.embed_documents.call_args_list] == [
        [c.embedding_text for c in chunks[:2]], [chunks[2].embedding_text]]
    assert store.collection.count() == 3
    manifest = dict(status="indexed", directory=str(tmp_path), query_vector=[1.0, 0.0],
                    collections={"corpus_test": records})
    path = tmp_path / "manifest.json"
    save_manifest(path, manifest)
    result = subprocess.run([sys.executable, "-m", "scripts.index_corpus", "--verify", str(path)],
                            cwd=PROJECT_ROOT, capture_output=True, text=True, timeout=120)
    assert result.returncode == 0, result.stdout + result.stderr
    # La huella debe detectar incluso una modificación de metadata.
    key = next(iter(records))
    store.collection.update(ids=[key], metadatas=[{"page_end": 99}])
    with pytest.raises(ValueError, match="alterados"):
        verify_saved(path)


def test_incomplete_run_cannot_be_verified(tmp_path):
    path = tmp_path / "manifest.json"
    save_manifest(path, {"status": "in_progress"})
    with pytest.raises(ValueError, match="incompleta"):
        verify_saved(path)


def test_invalid_batch_size_fails_before_embedding():
    store = Mock()
    with pytest.raises(ValueError, match="batch_size"):
        index_chunks(store, [], batch_size=0)
    store.add_chunks.assert_not_called()


@pytest.mark.parametrize("index", [False, True])
def test_main_separates_configurations_and_loads_model_only_for_index(tmp_path, monkeypatch, index):
    import scripts.index_corpus as script
    import src.indexing.embeddings as embeddings
    from src.common.tokenization import Tokenization
    from src.ingestion.loaders import LoadedPage

    class Tokenizer:
        name_or_path = "fake"
        model_max_length = 512
        def encode(self, text, *, add_special_tokens, truncation):
            return list(range(len(text) + (2 if add_special_tokens else 0)))

    raw = tmp_path / "data" / "raw"
    raw.mkdir(parents=True)
    (raw / "sample.pdf").write_bytes(b"fake PDF: loader injected")
    source = dict(filename="sample.pdf", doc_id="sample", tax="IVA", doc_type="law")
    monkeypatch.setattr(script, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(script, "check_corpus", lambda: [source])
    monkeypatch.setattr(script, "load_clean_pages", lambda source: [LoadedPage("texto fiscal " * 60, 1)])
    monkeypatch.setattr(script, "load_tokenization", lambda settings: Tokenization(Tokenizer(), 512, "passage: "))
    monkeypatch.setattr(script, "get_settings", lambda: Settings(_env_file=None, chroma_dir=str(tmp_path / "db")))
    service = Mock()
    service.embed_documents.side_effect = lambda texts: [[1.0, 0.0] for _ in texts]
    service.embed_query.return_value = [1.0, 0.0]
    factory = Mock(return_value=service)
    monkeypatch.setattr(embeddings, "EmbeddingService", factory)
    # La prueba anterior ya comprueba el proceso hijo real.
    monkeypatch.setattr(script.subprocess, "run", lambda command, **kwargs: verify_saved(command[-1]))
    script.main(["--index"] if index else [])
    if index:
        factory.assert_called_once()
        service.embed_query.assert_called_once()
        manifests = list((tmp_path / "db").rglob("manifest.json"))
        assert len(manifests) == 1
        manifest = json.loads(manifests[0].read_text(encoding="utf-8"))
        assert manifest["status"] == "verified"
        assert set(manifest["collections"]) == {"corpus_256_32", "corpus_384_48", "corpus_480_64"}
        assert all(manifest["collections"].values())
    else:
        factory.assert_not_called()
        assert not (tmp_path / "db").exists()


def test_windows_non_ascii_storage_fails_early(monkeypatch, tmp_path):
    import scripts.index_corpus as script
    monkeypatch.setattr(script.sys, "platform", "win32")
    with pytest.raises(ValueError, match="CHROMA_DIR"):
        script.validate_storage_path(tmp_path / "módulo")
    assert script.validate_storage_path(tmp_path / "ascii") == (tmp_path / "ascii").resolve()


def test_persistence_above_hnsw_sync_threshold(tmp_path):
    store = get_vectorstore(Settings(_env_file=None, chroma_dir=str(tmp_path),
                                    chroma_collection="threshold_probe"))
    # Supera el umbral de persistencia: las muestras de pocos chunks no lo cubren.
    store.collection.add(ids=[str(i) for i in range(1100)],
                         embeddings=[[1.0, 0.0] for _ in range(1100)])
    code = ("import chromadb,sys; c=chromadb.PersistentClient(path=sys.argv[1])"
            ".get_collection('threshold_probe',embedding_function=None); "
            "assert c.count()==1100; "
            "assert len(c.query(query_embeddings=[[1.,0.]],n_results=4)['ids'][0])==4")
    result = subprocess.run([sys.executable, "-c", code, str(tmp_path)],
                            capture_output=True, text=True, timeout=120)
    assert result.returncode == 0, result.stdout + result.stderr


@pytest.mark.parametrize("collections", [{}, {"empty": {}}])
def test_empty_manifest_is_not_a_successful_run(tmp_path, collections):
    path = tmp_path / "manifest.json"
    save_manifest(path, {"status": "indexed", "collections": collections})
    with pytest.raises(ValueError, match="vacías"):
        verify_saved(path)


def test_document_without_text_is_rejected():
    from scripts.index_corpus import validate_chunks
    from src.ingestion.loaders import LoadedPage
    metadata = ChunkMetadata(doc_id="empty", doc_type="law", source_scope="public")
    with pytest.raises(ValueError, match="sin texto útil"):
        validate_chunks([], [LoadedPage("  ", 1)], metadata, None, None)
