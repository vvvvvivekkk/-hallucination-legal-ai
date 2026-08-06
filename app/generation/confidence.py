from __future__ import annotations

from typing import Any

from ..core.logger import get_logger
from .models import (
    Citation,
    ConfidenceReport,
    HallucinationReport,
    SourceChunk,
    VerificationReport,
)
from .text import clamp, containment, mean, overlap, sentences, significant_tokens


class ConfidenceScorer:
    """Composite confidence from faithfulness, answer relevance, and context metrics."""

    def __init__(
        self,
        weights: tuple[float, float, float, float] = (0.4, 0.2, 0.2, 0.2),
        logger: object | None = None,
    ) -> None:
        self._weights = weights
        self._logger = logger or get_logger(self.__class__.__name__)

    def score(
        self,
        query: str,
        answer: str,
        chunks: list[SourceChunk],
        verification: VerificationReport | None = None,
        hallucination: HallucinationReport | None = None,
    ) -> ConfidenceReport:
        faithfulness = self._faithfulness(query, answer, chunks, verification, hallucination)
        relevance = self._answer_relevance(query, answer)
        precision = self._context_precision(answer, chunks)
        recall = self._context_recall(answer, chunks)

        faith_weight, rel_weight, prec_weight, rec_weight = self._weights
        overall = clamp(
            faith_weight * faithfulness
            + rel_weight * relevance
            + prec_weight * precision
            + rec_weight * recall
        )
        return ConfidenceReport(
            faithfulness=faithfulness,
            answer_relevance=relevance,
            context_precision=precision,
            context_recall=recall,
            overall=overall,
        )

    @staticmethod
    def _faithfulness(
        query: str,
        answer: str,
        chunks: list[SourceChunk],
        verification: VerificationReport | None,
        hallucination: HallucinationReport | None,
    ) -> float:
        if verification is not None and verification.total_citations > 0:
            faithfulness = verification.grounding_score
        else:
            answer_tokens = significant_tokens(answer)
            chunk_tokens = [
                token
                for chunk in chunks
                for token in significant_tokens(chunk.text)
            ]
            faithfulness = containment(answer_tokens, chunk_tokens)
        if hallucination is not None:
            faithfulness = (faithfulness + (1.0 - hallucination.score)) / 2.0
        return clamp(faithfulness)

    @staticmethod
    def _answer_relevance(query: str, answer: str) -> float:
        return overlap(significant_tokens(query), significant_tokens(answer))

    @staticmethod
    def _context_precision(answer: str, chunks: list[SourceChunk]) -> float:
        if not chunks:
            return 0.0
        answer_tokens = significant_tokens(answer)
        if not answer_tokens:
            return 0.0
        used = sum(
            1
            for chunk in chunks
            if overlap(significant_tokens(chunk.text), answer_tokens) >= 0.05
        )
        return round(used / len(chunks), 4)

    @staticmethod
    def _context_recall(answer: str, chunks: list[SourceChunk]) -> float:
        if not chunks:
            return 0.0
        chunk_token_lists = [significant_tokens(chunk.text) for chunk in chunks]
        scores = [
            max(
                (containment(significant_tokens(sentence), tokens) for tokens in chunk_token_lists),
                default=0.0,
            )
            for sentence in sentences(answer)
        ]
        return mean(scores)
