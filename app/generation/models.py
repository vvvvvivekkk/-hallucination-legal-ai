from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class SourceChunk:
    index: int
    chunk_id: str
    doc_id: str
    text: str
    score: float = 0.0
    doc_title: str | None = None
    source_file: str | None = None
    section: str | None = None
    section_number: str | None = None
    page: int | None = None
    summary: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_payload(cls, index: int, payload: dict[str, Any]) -> "SourceChunk":
        return cls(
            index=index,
            chunk_id=payload.get("chunk_id", ""),
            doc_id=payload.get("doc_id", ""),
            text=payload.get("chunk_text", "") or payload.get("text", ""),
            score=float(payload.get("score", 0.0) or 0.0),
            doc_title=payload.get("doc_title"),
            source_file=payload.get("source_file"),
            section=payload.get("section"),
            section_number=payload.get("section_number"),
            page=payload.get("page"),
            summary=payload.get("summary"),
            metadata={
                key: value
                for key, value in payload.items()
                if key not in {"chunk_id", "doc_id", "chunk_text", "text", "score"}
            },
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class Citation:
    index: int
    marker: str
    start: int
    end: int
    chunk_id: str | None = None
    verified: bool = False
    supported: bool = False
    evidence_score: float = 0.0
    section_match: bool = True
    reason: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class CitationCheck:
    index: int
    chunk_id: str | None
    verified: bool
    supported: bool
    evidence_score: float
    section_match: bool
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class VerificationReport:
    checks: list[CitationCheck] = field(default_factory=list)
    grounding_score: float = 0.0
    verified_citations: int = 0
    total_citations: int = 0
    missing_citations: list[int] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "checks": [check.to_dict() for check in self.checks],
            "grounding_score": self.grounding_score,
            "verified_citations": self.verified_citations,
            "total_citations": self.total_citations,
            "missing_citations": self.missing_citations,
        }


@dataclass
class HallucinationFinding:
    category: str
    severity: str
    detail: str
    sentence: str | None = None
    evidence_score: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class HallucinationReport:
    score: float = 0.0
    verdict: str = "low"
    findings: list[HallucinationFinding] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "score": self.score,
            "verdict": self.verdict,
            "findings": [finding.to_dict() for finding in self.findings],
        }


@dataclass
class ConfidenceReport:
    faithfulness: float = 0.0
    answer_relevance: float = 0.0
    context_precision: float = 0.0
    context_recall: float = 0.0
    overall: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class VerifiedResponse:
    query: str
    answer: str
    model: str = ""
    session_id: str | None = None
    elapsed_ms: int = 0
    quality_score: float = 0.0
    rank: int | None = None
    sources: list[SourceChunk] = field(default_factory=list)
    citations: list[Citation] = field(default_factory=list)
    verification: VerificationReport | None = None
    hallucination: HallucinationReport | None = None
    confidence: ConfidenceReport | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "query": self.query,
            "answer": self.answer,
            "model": self.model,
            "session_id": self.session_id,
            "elapsed_ms": self.elapsed_ms,
            "quality_score": self.quality_score,
            "rank": self.rank,
            "sources": [source.to_dict() for source in self.sources],
            "citations": [citation.to_dict() for citation in self.citations],
            "verification": self.verification.to_dict() if self.verification else None,
            "hallucination": self.hallucination.to_dict() if self.hallucination else None,
            "confidence": self.confidence.to_dict() if self.confidence else None,
        }
