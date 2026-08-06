from __future__ import annotations

from typing import Any

from ..core.logger import get_logger
from .base import RankedResult


class CrossEncoderReranker:
    def __init__(
        self,
        model_name: str = "cross-encoder/ms-marco-MiniLM-L6-v2",
        device: str | None = None,
        logger: object | None = None,
    ) -> None:
        self._model_name = model_name
        self._device = device
        self._logger = logger or get_logger(self.__class__.__name__)
        self._model: Any | None = None

    def _load(self) -> Any:
        if self._model is None:
            from sentence_transformers import CrossEncoder

            self._model = CrossEncoder(self._model_name, device=self._device)
        return self._model

    def rerank(
        self,
        query: str,
        results: list[RankedResult],
        top_k: int = 5,
        blend: float = 0.5,
    ) -> list[RankedResult]:
        if not results:
            return results
        model = self._load()
        pairs = [(query, result.payload.get("chunk_text") or "") for result in results]
        scores = model.predict(pairs)
        reranked: list[RankedResult] = []
        for result, score in zip(results, scores):
            merged = (blend * float(score)) + ((1 - blend) * result.score)
            reranked.append(
                RankedResult(
                    chunk_id=result.chunk_id,
                    score=merged,
                    payload=result.payload,
                    dense_score=result.dense_score,
                    lexical_score=result.lexical_score,
                    rank=None,
                )
            )
        reranked.sort(key=lambda item: item.score, reverse=True)
        for index, result in enumerate(reranked, start=1):
            result.rank = index
        return reranked[:top_k]
