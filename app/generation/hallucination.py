from __future__ import annotations

from typing import Any

from ..core.logger import get_logger
from .citations import citation_indices_in_sentence
from .models import (
    Citation,
    HallucinationFinding,
    HallucinationReport,
    SourceChunk,
    VerificationReport,
)
from .text import best_containment, containment, sentences, significant_tokens

_NEGATORS = {
    "not", "no", "never", "cannot", "cant", "won't", "wont", "without",
    "except", "nor", "neither", "none", "lack", "absence",
}

_SEVERITY_WEIGHTS = {"high": 1.0, "medium": 0.5, "low": 0.25}

_CATEGORIES = {
    "unsupported_claim",
    "unsupported_citation",
    "missing_evidence",
    "contradicting_evidence",
}


def _detect_contradiction(claim: str, evidence: str, threshold: float) -> bool:
    claim_tokens = significant_tokens(claim)
    evidence_tokens = significant_tokens(evidence)
    if not claim_tokens or not evidence_tokens:
        return False
    overlap = containment(claim_tokens, evidence_tokens)
    if overlap < threshold:
        return False
    claim_negated = bool(set(claim_tokens) & _NEGATORS)
    evidence_negated = bool(set(evidence_tokens) & _NEGATORS)
    return claim_negated != evidence_negated


class HallucinationDetector:
    """Deterministic claim-level hallucination detection over the generated answer."""

    def __init__(
        self,
        claim_threshold: float = 0.25,
        contradiction_threshold: float = 0.6,
        logger: object | None = None,
    ) -> None:
        self._claim_threshold = claim_threshold
        self._contradiction_threshold = contradiction_threshold
        self._logger = logger or get_logger(self.__class__.__name__)

    def detect(
        self,
        query: str,
        answer: str,
        chunks: list[SourceChunk],
        citations: list[Citation],
        verification: VerificationReport | None = None,
    ) -> HallucinationReport:
        findings: list[HallucinationFinding] = []
        by_index = {citation.index: citation for citation in citations}
        chunk_token_lists = [significant_tokens(chunk.text) for chunk in chunks]

        for citation in citations:
            if not citation.verified:
                findings.append(
                    HallucinationFinding(
                        category="unsupported_citation",
                        severity="medium",
                        detail=f"Citation [{citation.index}] does not match any retrieved source chunk",
                        sentence=answer[citation.start : citation.end] or None,
                    )
                )
            elif not citation.supported:
                findings.append(
                    HallucinationFinding(
                        category="unsupported_claim",
                        severity="medium",
                        detail=(
                            f"Claim cited as [{citation.index}] has insufficient evidence "
                            f"overlap (score {citation.evidence_score:.2f})"
                        ),
                        evidence_score=citation.evidence_score,
                    )
                )

        for sentence in sentences(answer):
            cited = [
                index
                for index in citation_indices_in_sentence(sentence)
                if index in by_index
            ]
            if not cited:
                if "?" in sentence:
                    continue
                overlap = best_containment(significant_tokens(sentence), chunk_token_lists)
                if overlap < self._claim_threshold:
                    findings.append(
                        HallucinationFinding(
                            category="missing_evidence",
                            severity="low",
                            detail="Uncited claim with no supporting evidence in the retrieved context",
                            sentence=sentence,
                            evidence_score=overlap,
                        )
                    )
                continue
            for index in cited:
                citation = by_index[index]
                chunk = next((item for item in chunks if item.index == index), None)
                if chunk is None:
                    continue
                if _detect_contradiction(
                    sentence, chunk.text, self._contradiction_threshold
                ):
                    findings.append(
                        HallucinationFinding(
                            category="contradicting_evidence",
                            severity="high",
                            detail=(
                                f"Claim cited as [{index}] contradicts its source "
                                "(negation mismatch detected)"
                            ),
                            sentence=sentence,
                            evidence_score=citation.evidence_score,
                        )
                    )

        score = self._score(findings, answer, citations)
        verdict = self.verdict_for(score)
        return HallucinationReport(
            score=score,
            verdict=verdict,
            findings=findings,
        )

    @staticmethod
    def _score(
        findings: list[HallucinationFinding],
        answer: str,
        citations: list[Citation],
    ) -> float:
        total_weight = sum(_SEVERITY_WEIGHTS.get(item.severity, 0.5) for item in findings)
        denominator = max(1, len(sentences(answer)) + len(citations))
        return round(min(1.0, total_weight / denominator), 4)

    @staticmethod
    def verdict_for(score: float) -> str:
        if score >= 0.5:
            return "high"
        if score >= 0.25:
            return "medium"
        return "low"
