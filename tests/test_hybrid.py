from __future__ import annotations

import numpy as np

from app.retrieval.base import RankedResult
from app.retrieval.hybrid import HybridRetriever, rrf_fusion


def _result(chunk_id: str, score: float, dense: float | None = None, lexical: float | None = None) -> RankedResult:
    return RankedResult(
        chunk_id=chunk_id,
        score=score,
        payload={"doc_id": "d"},
        dense_score=dense,
        lexical_score=lexical,
    )


def test_rrf_prefers_consensus() -> None:
    dense = [_result("a", 0.9), _result("b", 0.8)]
    lexical = [_result("b", 0.9), _result("c", 0.7)]
    fused = rrf_fusion([dense, lexical], k=60)
    assert [result.chunk_id for result in fused] == ["b", "a", "c"]


def test_rrf_weights() -> None:
    dense = [_result("a", 0.9), _result("b", 0.8)]
    lexical = [_result("b", 0.9), _result("a", 0.8)]
    dense_only = rrf_fusion([dense, lexical], k=60, weights=[1.0, 0.0])
    assert dense_only[0].chunk_id == "a"
    lexical_only = rrf_fusion([dense, lexical], k=60, weights=[0.0, 1.0])
    assert lexical_only[0].chunk_id == "b"


def test_rrf_empty() -> None:
    assert rrf_fusion([]) == []
    assert rrf_fusion([[], []]) == []


class FakeDense:
    def __init__(self, results: list[RankedResult]) -> None:
        self.results = results

    def semantic_search(
        self, query_vector: np.ndarray, top_k: int = 10, conditions: dict | None = None
    ) -> list[RankedResult]:
        return self.results[:top_k]


class FakeLexical:
    def __init__(self, results: list[RankedResult]) -> None:
        self.results = results

    def search(self, query: str, top_k: int = 10, conditions: dict | None = None) -> list[RankedResult]:
        return self.results[:top_k]


class FakeEmbedder:
    def embed_query(self, text: str) -> np.ndarray:
        return np.zeros(4, dtype=np.float32)


def test_hybrid_retriever_fusion() -> None:
    dense = FakeDense([_result("a", 0.9, dense=0.9), _result("b", 0.8, dense=0.8)])
    lexical = FakeLexical([_result("b", 0.9, lexical=0.9), _result("c", 0.7, lexical=0.7)])
    retriever = HybridRetriever(
        dense_searcher=dense,
        lexical_searcher=lexical,
        embedder=FakeEmbedder(),
        top_k=3,
        rrf_k=60,
        dense_weight=0.5,
    )
    results = retriever.search("punishment for murder")
    assert [result.chunk_id for result in results] == ["b", "a", "c"]
    assert results[0].dense_score == 0.8
    assert results[0].lexical_score == 0.9
