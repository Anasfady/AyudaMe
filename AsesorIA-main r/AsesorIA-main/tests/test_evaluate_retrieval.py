"""Métricas y búsqueda de evaluación: sin descargar modelos."""
import json
from unittest.mock import Mock

import pytest

from scripts.evaluate_retrieval import (evaluate, load_questions, score_question,
                                         summarize, retrieve_ranked)
from scripts.index_corpus import record_digest


def result(doc="expected", start=7, end=8, tokens=100):
    return {"metadata": {"doc_id": doc, "page": start, "page_end": end}, "text_tokens": tokens}


def test_page_hit_requires_correct_document_and_inclusive_range():
    q = {"expected_doc_id": "expected", "expected_page": 8}
    assert score_question(q, [result(doc="other")], 3)["page_hit"] is False
    assert score_question(q, [result()], 3)["page_hit"] is True
    assert score_question(q, [result(end=7)], 3)["page_hit"] is False


def test_top_k_and_duplicates_count_one_question_hit():
    q = {"expected_doc_id": "expected", "expected_page": 8}
    ranking = [result(doc="other"), result(), result()]
    assert score_question(q, ranking, 1)["document_hit"] is False
    assert score_question(q, ranking, 2)["page_hit"] is True
    assert score_question(q, ranking, 3)["text_tokens"] == 300
    assert score_question(q, [], 3)["page_hit"] is False


def test_missing_labels_are_excluded_from_denominators():
    rows = [{"scores": {"3": score_question(q, [result()], 3)}} for q in [
        {"expected_doc_id": "expected", "expected_page": 8},
        {"expected_doc_id": "expected"}, {}, {"expected_doc_id": "other", "expected_page": 8}]]
    summary = summarize(rows, 3)
    assert summary["document_hit"] == {"hits": 2, "evaluated": 3, "rate": 2/3}
    assert summary["page_hit"] == {"hits": 1, "evaluated": 2, "rate": .5}
    assert summarize([], 3)["page_hit"]["rate"] is None


def test_benchmark_utf16_and_duplicate_validation(tmp_path):
    path = tmp_path / "benchmark.json"
    q = {"id": "q1", "question": "Pregunta", "expected_doc_id": "expected", "expected_page": 8}
    path.write_text(json.dumps({"questions": [q]}), encoding="utf-16")
    assert load_questions(path, {"expected": 10})[0] == [q]
    with pytest.raises(ValueError, match="página"):
        load_questions(path, {"expected": 7})
    path.write_text(json.dumps({"questions": [q, q]}), encoding="utf-16")
    with pytest.raises(ValueError, match="duplicado"):
        load_questions(path, {"expected": 10})


def test_same_query_vector_reused_without_answer_label_filters():
    metadata = {"doc_id": "expected", "page": 7, "page_end": 8, "source_scope": "public"}
    raw = {"ids": [["id1"]], "documents": [["original"]], "metadatas": [[metadata]], "distances": [[.25]]}
    stores = {name: Mock() for name in ["small", "large"]}
    for store in stores.values():
        store.query.return_value = raw
    service, tokenizer = Mock(), Mock()
    service.embed_query.return_value = [1., 0.]
    tokenizer.count.return_value = 10
    q = {"id": "q1", "question": "consulta sin prefijo", "expected_doc_id": "expected", "expected_page": 8}
    records = {name: {"id1": record_digest("original", metadata)} for name in stores}
    report = evaluate([q], stores, service, tokenizer, records)
    service.embed_query.assert_called_once_with("consulta sin prefijo")
    for name, store in stores.items():
        store.query.assert_called_once_with([1., 0.], top_k=8, filter_dict={"source_scope": "public"})
        row = report[name]["questions"][0]
        assert row["ranked"][0]["text"] == "original"
        assert row["ranked"][0]["cosine_similarity"] == .75
        assert row["scores"]["3"]["page_hit"] is True
    metadata["source_scope"] = "private"
    with pytest.raises(ValueError, match="públicos"):
        retrieve_ranked(stores["small"], [1., 0.], tokenizer, records["small"])


def test_changed_record_is_rejected():
    store = Mock()
    store.query.return_value = {"ids": [["id1"]], "documents": [["alterado"]],
        "metadatas": [[{"source_scope": "public"}]], "distances": [[.1]]}
    with pytest.raises(ValueError, match="diferente"):
        retrieve_ranked(store, [1., 0.], Mock(), {"id1": "different digest"})


def test_open_existing_collection_uses_compatible_settings_and_never_creates_missing(tmp_path):
    from src.common.settings import Settings
    from src.indexing.vectorstore import get_vectorstore
    from scripts.evaluate_retrieval import open_stores
    from chromadb.errors import NotFoundError
    settings = Settings(_env_file=None, chroma_dir=str(tmp_path), chroma_collection="existing")
    store = get_vectorstore(settings)
    store.collection.add(ids=["one"], embeddings=[[1., 0.]])
    manifest = {"collections": {"existing": {"one": "digest"}}}
    assert open_stores(manifest, settings)["existing"].collection.count() == 1
    with pytest.raises(NotFoundError):
        open_stores({"collections": {"missing": {"one": "digest"}}}, settings)
    assert [c.name for c in store.client.list_collections()] == ["existing"]
