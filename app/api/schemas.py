from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class IngestRequest(BaseModel):
    path: str | None = None
    collection: str | None = None
    enable_dedup: bool = True


class IngestResponse(BaseModel):
    job_id: str
    status: str
    message: str


class IndexRequest(BaseModel):
    collection: str | None = None


class ReindexRequest(BaseModel):
    collection: str | None = None
    path: str | None = None
    enable_dedup: bool = True


class JobResponse(BaseModel):
    job_id: str
    kind: str
    status: str
    progress: float
    message: str
    error: str | None = None
    stats: dict[str, Any] = Field(default_factory=dict)
    created_at: str
    updated_at: str


class SearchFilters(BaseModel):
    doc_ids: list[str] | None = None
    source_files: list[str] | None = None
    doc_titles: list[str] | None = None
    courts: list[str] | None = None
    jurisdictions: list[str] | None = None
    doc_types: list[str] | None = None
    sections: list[str] | None = None
    section_numbers: list[str] | None = None
    pages: list[int] | None = None
    year_min: int | None = None
    year_max: int | None = None

    def to_conditions(self) -> dict[str, Any]:
        conditions: dict[str, Any] = {}
        mapping = {
            "doc_ids": "doc_id",
            "source_files": "source_file",
            "doc_titles": "doc_title",
            "courts": "court",
            "jurisdictions": "jurisdiction",
            "doc_types": "doc_type",
            "sections": "section",
            "section_numbers": "section_number",
            "pages": "page",
        }
        for attribute, field_name in mapping.items():
            value = getattr(self, attribute)
            if value is not None:
                conditions[field_name] = value
        if self.year_min is not None or self.year_max is not None:
            bounds: dict[str, int] = {}
            if self.year_min is not None:
                bounds["min"] = self.year_min
            if self.year_max is not None:
                bounds["max"] = self.year_max
            conditions["year"] = bounds
        return conditions


class SearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=2000)
    collection: str | None = None
    top_k: int | None = Field(default=None, ge=1, le=100)
    filters: SearchFilters | None = None
    dense_weight: float | None = Field(default=None, ge=0.0, le=1.0)


class SearchHit(BaseModel):
    chunk_id: str
    doc_id: str
    score: float
    text: str
    summary: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    dense_score: float | None = None
    lexical_score: float | None = None


class SearchResponse(BaseModel):
    query: str
    collection: str
    total: int
    elapsed_ms: int
    results: list[SearchHit]


class HealthResponse(BaseModel):
    status: str
    service: str
    version: str
    collection: str
    points: int | None = None
    qdrant: str
    uptime_seconds: float


class SourceChunkModel(BaseModel):
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


class CitationModel(BaseModel):
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


class CitationCheckModel(BaseModel):
    index: int
    chunk_id: str | None
    verified: bool
    supported: bool
    evidence_score: float
    section_match: bool
    reason: str


class VerificationModel(BaseModel):
    checks: list[CitationCheckModel] = Field(default_factory=list)
    grounding_score: float = 0.0
    verified_citations: int = 0
    total_citations: int = 0
    missing_citations: list[int] = Field(default_factory=list)


class HallucinationFindingModel(BaseModel):
    category: str
    severity: str
    detail: str
    sentence: str | None = None
    evidence_score: float | None = None


class HallucinationModel(BaseModel):
    score: float = 0.0
    verdict: str = "low"
    findings: list[HallucinationFindingModel] = Field(default_factory=list)


class ConfidenceModel(BaseModel):
    faithfulness: float = 0.0
    answer_relevance: float = 0.0
    context_precision: float = 0.0
    context_recall: float = 0.0
    overall: float = 0.0


class VerifiedResponseModel(BaseModel):
    query: str
    answer: str
    model: str = ""
    session_id: str | None = None
    elapsed_ms: int = 0
    quality_score: float = 0.0
    rank: int | None = None
    sources: list[SourceChunkModel] = Field(default_factory=list)
    citations: list[CitationModel] = Field(default_factory=list)
    verification: VerificationModel | None = None
    hallucination: HallucinationModel | None = None
    confidence: ConfidenceModel | None = None


class ChatRequest(BaseModel):
    query: str = Field(min_length=1, max_length=2000)
    session_id: str | None = None
    stream: bool = False
    filters: SearchFilters | None = None
    top_k: int | None = Field(default=None, ge=1, le=20)
    num_responses: int | None = Field(default=None, ge=1, le=3)
    store_history: bool = True


class ChatResponse(BaseModel):
    session_id: str | None = None
    result: VerifiedResponseModel | None = None


class QueryRequest(BaseModel):
    query: str = Field(min_length=1, max_length=2000)
    session_id: str | None = None
    filters: SearchFilters | None = None
    top_k: int | None = Field(default=None, ge=1, le=20)
    num_responses: int | None = Field(default=None, ge=1, le=3)


class QueryResponse(BaseModel):
    session_id: str | None = None
    result: VerifiedResponseModel


class VerifyRequest(BaseModel):
    query: str = Field(min_length=1, max_length=2000)
    answer: str = Field(min_length=1, max_length=16000)
    context: list[dict[str, Any]] | None = None
    filters: SearchFilters | None = None
    top_k: int | None = Field(default=None, ge=1, le=20)


class VerifyResponse(BaseModel):
    result: VerifiedResponseModel


class CitationsRequest(BaseModel):
    query: str = Field(min_length=1, max_length=2000)
    answer: str = Field(min_length=1, max_length=16000)
    context: list[dict[str, Any]] | None = None
    filters: SearchFilters | None = None
    top_k: int | None = Field(default=None, ge=1, le=20)


class CitationsResponse(BaseModel):
    query: str
    answer: str
    citations: list[CitationModel] = Field(default_factory=list)
    sources: list[SourceChunkModel] = Field(default_factory=list)


class HallucinationRequest(BaseModel):
    query: str = Field(min_length=1, max_length=2000)
    answer: str = Field(min_length=1, max_length=16000)
    context: list[dict[str, Any]] | None = None
    filters: SearchFilters | None = None
    top_k: int | None = Field(default=None, ge=1, le=20)


class HallucinationResponse(BaseModel):
    query: str
    answer: str
    hallucination: HallucinationModel


class ConfidenceRequest(BaseModel):
    query: str = Field(min_length=1, max_length=2000)
    answer: str = Field(min_length=1, max_length=16000)
    context: list[dict[str, Any]] | None = None
    filters: SearchFilters | None = None
    top_k: int | None = Field(default=None, ge=1, le=20)


class ConfidenceResponse(BaseModel):
    query: str
    answer: str
    confidence: ConfidenceModel
    verification: VerificationModel | None = None
    sources: list[SourceChunkModel] = Field(default_factory=list)
