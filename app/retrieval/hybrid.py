from __future__ import annotations

from typing import Any

from ..core.exceptions import RetrievalError
from ..core.logger import get_logger
from .base import DenseSearcher, LexicalSearcher, RankedResult


def rrf_fusion(
    system_results: list[list[RankedResult]],
    k: int = 60,
    weights: list[float] | None = None,
) -> list[RankedResult]:
    fused: dict[str, RankedResult] = {}
    for system_index, results in enumerate(system_results):
        weight = weights[system_index] if weights else 1.0
        for rank, result in enumerate(results, start=1):
            current = fused.get(result.chunk_id)
            if current is None:
                current = RankedResult(
                    chunk_id=result.chunk_id,
                    score=0.0,
                    payload=result.payload,
                )
                fused[result.chunk_id] = current
            current.score += weight / (k + rank)
            if result.dense_score is not None:
                if current.dense_score is None:
                    current.dense_score = result.dense_score
                else:
                    current.dense_score = max(current.dense_score, result.dense_score)
            if result.lexical_score is not None:
                if current.lexical_score is None:
                    current.lexical_score = result.lexical_score
                else:
                    current.lexical_score = max(current.lexical_score, result.lexical_score)

    ranked = sorted(fused.values(), key=lambda result: result.score, reverse=True)
    for index, result in enumerate(ranked, start=1):
        result.rank = index
    return ranked


class HybridRetriever:
    def __init__(
        self,
        dense_searcher: DenseSearcher,
        lexical_searcher: LexicalSearcher,
        embedder: Any,
        top_k: int = 10,
        rrf_k: int = 60,
        dense_weight: float = 0.5,
        reranker: Any | None = None,
        rerank_top_k: int = 5,
        logger: object | None = None,
    ) -> None:
        self._dense = dense_searcher
        self._lexical = lexical_searcher
        self._embedder = embedder
        self._top_k = top_k
        self._rrf_k = rrf_k
        self._dense_weight = dense_weight
        self._reranker = reranker
        self._rerank_top_k = rerank_top_k
        self._logger = logger or get_logger(self.__class__.__name__)

    def search(
        self,
        query: str,
        top_k: int | None = None,
        conditions: dict[str, Any] | None = None,
        dense_weight: float | None = None,
    ) -> list[RankedResult]:
        try:
            query_vector = self._embedder.embed_query(query)
        except Exception as exc:
            raise RetrievalError("Failed to embed query", cause=exc)

        pool = top_k or self._top_k
        dense_results = self._dense.semantic_search(
            query_vector, top_k=pool, conditions=conditions
        )
        lexical_results = self._lexical.search(query, top_k=pool, conditions=conditions)

        weight = dense_weight if dense_weight is not None else self._dense_weight
        fused = rrf_fusion(
            [dense_results, lexical_results],
            k=self._rrf_k,
            weights=[weight, 1.0 - weight],
        )
        results = fused[:pool]

        if self._reranker is not None and self._rerank_top_k > 0 and results:
            results = self._reranker.rerank(query, results, self._rerank_top_k)
        return results
