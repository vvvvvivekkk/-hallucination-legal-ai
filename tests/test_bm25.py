from __future__ import annotations

from app.retrieval.bm25 import LocalBm25Index, tokenize


def test_tokenize_legal() -> None:
    assert "§" in tokenize("Section 300 § 302")
    assert tokenize("The Indian Penal Code, 1860") == ["the", "indian", "penal", "code", "1860"]


def test_search_ranking() -> None:
    index = LocalBm25Index(k1=1.5, b=0.75)
    index.build(
        [
            ("c1", "murder punishment imprisonment life death", {"doc_id": "d1", "chunk_id": "c1"}),
            ("c2", "contract agreement consideration breach", {"doc_id": "d2", "chunk_id": "c2"}),
            ("c3", "murder criminal trial evidence witness", {"doc_id": "d3", "chunk_id": "c3"}),
        ]
    )
    results = index.search("punishment for murder", top_k=5)
    assert results
    assert results[0].chunk_id == "c1"
    assert results[0].lexical_score is not None
    assert results[0].lexical_score > results[1].lexical_score
    assert results[2].chunk_id == "c2"


def test_search_filter_range() -> None:
    index = LocalBm25Index()
    index.build(
        [
            ("c1", "murder punishment", {"doc_id": "d1", "year": 2020, "chunk_id": "c1"}),
            ("c2", "murder punishment", {"doc_id": "d2", "year": 2000, "chunk_id": "c2"}),
        ]
    )
    results = index.search("murder", top_k=5, conditions={"year": {"min": 2019}})
    assert len(results) == 1
    assert results[0].payload["doc_id"] == "d1"


def test_search_filter_list() -> None:
    index = LocalBm25Index()
    index.build(
        [
            ("c1", "murder punishment", {"doc_id": "d1", "court": "Supreme Court", "chunk_id": "c1"}),
            ("c2", "murder punishment", {"doc_id": "d2", "court": "High Court", "chunk_id": "c2"}),
        ]
    )
    results = index.search("murder", top_k=5, conditions={"court": ["High Court"]})
    assert len(results) == 1
    assert results[0].payload["doc_id"] == "d2"


def test_empty_index() -> None:
    index = LocalBm25Index()
    assert index.search("anything") == []


def test_save_load(tmp_path) -> None:
    store = tmp_path / "bm25.pkl"
    index = LocalBm25Index(store_path=store)
    index.build([("c1", "murder punishment", {"doc_id": "d1", "chunk_id": "c1"})])
    index.save()

    reloaded = LocalBm25Index(store_path=store)
    assert reloaded.load() is True
    results = reloaded.search("murder")
    assert results[0].chunk_id == "c1"
