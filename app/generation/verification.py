from __future__ import annotations

import re
from typing import Any

from ..core.logger import get_logger
from .citations import citation_indices_in_sentence
from .models import Citation, CitationCheck, SourceChunk, VerificationReport
from .text import best_containment, containment, mean, sentences, significant_tokens

_SECTION_REF_RE = re.compile(r"(?:section|sec\.?|s\.)\s*(\d+[a-zA-Z]?(?:\.\d+)*)", re.IGNORECASE)


def _claim_segment_for_index(answer: str, index: int) -> str:
    for sentence in sentences(answer):
        if index in citation_indices_in_sentence(sentence):
            return sentence
    return ""


def _normalize_section(value: str | None) -> str:
    if not value:
        return ""
    return re.sub(r"[^a-z0-9]", "", value.lower())


def _section_matches(claim: str, chunk: SourceChunk) -> bool:
    refs = [group for group in _SECTION_REF_RE.findall(claim)]
    if not refs:
        return True
    chunk_refs = {
        _normalize_section(chunk.section_number),
        _normalize_section(chunk.section),
    }
    for reference in refs:
        if _normalize_section(reference) in chunk_refs:
            return True
    return False


class CitationVerifier:
    """Reference, evidence, and legal-section verification of citations."""

    def __init__(
        self,
        min_overlap: float = 0.15,
        enable_section_check: bool = True,
        logger: object | None = None,
    ) -> None:
        self._min_overlap = min_overlap
        self._enable_section_check = enable_section_check
        self._logger = logger or get_logger(self.__class__.__name__)

    def verify(
        self,
        query: str,
        answer: str,
        chunks: list[SourceChunk],
        citations: list[Citation],
    ) -> VerificationReport:
        by_index = {chunk.index: chunk for chunk in chunks}
        chunk_token_lists = [significant_tokens(chunk.text) for chunk in chunks]
        checks: list[CitationCheck] = []
        evidence_scores: list[float] = []

        for citation in citations:
            chunk = by_index.get(citation.index)
            if chunk is None:
                citation.verified = False
                citation.supported = False
                citation.reason = "no matching source chunk"
                checks.append(
                    CitationCheck(
                        index=citation.index,
                        chunk_id=None,
                        verified=False,
                        supported=False,
                        evidence_score=0.0,
                        section_match=True,
                        reason="no matching source chunk",
                    )
                )
                continue
            claim = _claim_segment_for_index(answer, citation.index)
            evidence_score = (
                containment(significant_tokens(claim), significant_tokens(chunk.text))
                if claim
                else 0.0
            )
            section_match = (
                _section_matches(claim, chunk) if self._enable_section_check else True
            )
            supported = evidence_score >= self._min_overlap
            citation.chunk_id = chunk.chunk_id
            citation.verified = True
            citation.supported = supported
            citation.evidence_score = evidence_score
            citation.section_match = section_match
            reasons = ["reference found"]
            if not supported:
                reasons.append("insufficient evidence overlap")
            if not section_match:
                reasons.append("section mismatch")
            citation.reason = "; ".join(reasons)
            checks.append(
                CitationCheck(
                    index=citation.index,
                    chunk_id=chunk.chunk_id,
                    verified=True,
                    supported=supported,
                    evidence_score=evidence_score,
                    section_match=section_match,
                    reason=citation.reason,
                )
            )
            evidence_scores.append(evidence_score)

        if evidence_scores:
            grounding = mean(evidence_scores)
        else:
            answer_tokens = significant_tokens(answer)
            grounding = (
                best_containment(answer_tokens, chunk_token_lists)
                if answer_tokens and chunk_token_lists
                else 0.0
            )

        verified_citations = sum(1 for check in checks if check.verified and check.supported)
        missing_citations = sorted(
            {check.index for check in checks if check.chunk_id is None}
        )
        return VerificationReport(
            checks=checks,
            grounding_score=round(grounding, 4),
            verified_citations=verified_citations,
            total_citations=len(citations),
            missing_citations=missing_citations,
        )
