"""Generation pipeline: grounded answer synthesis, citation verification,
hallucination detection, and confidence scoring for legal RAG."""

from .models import (
    Citation,
    CitationCheck,
    ConfidenceReport,
    HallucinationFinding,
    HallucinationReport,
    SourceChunk,
    VerificationReport,
    VerifiedResponse,
)

__all__ = [
    "Citation",
    "CitationCheck",
    "ConfidenceReport",
    "HallucinationFinding",
    "HallucinationReport",
    "SourceChunk",
    "VerificationReport",
    "VerifiedResponse",
]
