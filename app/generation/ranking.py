from __future__ import annotations

from typing import Any

from ..core.logger import get_logger
from .models import VerifiedResponse
from .text import mean


class ResponseRanker:
    """Ranks candidate answers by faithfulness, relevance, and citation coverage."""

    def __init__(
        self,
        weights: tuple[float, float, float, float] = (0.4, 0.2, 0.2, 0.2),
        logger: object | None = None,
    ) -> None:
        self._weights = weights
        self._logger = logger or get_logger(self.__class__.__name__)

    def rank(self, candidates: list[VerifiedResponse]) -> list[VerifiedResponse]:
        if not candidates:
            return []
        for candidate in candidates:
            candidate.quality_score = self._score(candidate)
        ranked = sorted(candidates, key=lambda item: item.quality_score, reverse=True)
        for index, candidate in enumerate(ranked, start=1):
            candidate.rank = index
        return ranked

    def _score(self, candidate: VerifiedResponse) -> float:
        faith_weight, rel_weight, evidence_weight, hallucination_weight = self._weights
        confidence = candidate.confidence
        if confidence is None:
            return 0.0
        evidence = (
            mean([citation.evidence_score for citation in candidate.citations])
            if candidate.citations
            else 0.0
        )
        hallucination_score = (
            candidate.hallucination.score if candidate.hallucination is not None else 0.0
        )
        return round(
            faith_weight * confidence.faithfulness
            + rel_weight * confidence.answer_relevance
            + evidence_weight * evidence
            + hallucination_weight * (1.0 - hallucination_score),
            4,
        )
