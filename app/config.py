from __future__ import annotations

from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    project_name: str = "Legal AI RAG"
    environment: str = "development"
    version: str = "0.1.0"
    log_level: str = "INFO"
    log_json: bool = False

    qdrant_url: str = "http://localhost:6333"
    qdrant_api_key: str | None = None
    qdrant_collection: str = "legal_corpus"
    qdrant_prefer_grpc: bool = False
    qdrant_timeout_seconds: int = 30
    qdrant_max_retries: int = 3
    embedding_dim: int = 768

    embedding_model: str = "BAAI/bge-base-en-v1.5"
    embedding_device: str | None = None
    embedding_batch_size: int = 32
    embedding_cache_path: str = str(PROJECT_ROOT / "data" / "cache" / "embeddings.db")
    embedding_query_prefix: str = "Represent this sentence for searching relevant passages: "

    ingestion_dir: str = str(PROJECT_ROOT / "data" / "raw")
    enable_ocr_fallback: bool = True
    ocr_min_chars: int = 10
    ocr_dpi: int = 200
    enable_dedup: bool = True
    dedup_threshold: float = 0.85
    dedup_store_path: str = str(PROJECT_ROOT / "data" / "cache" / "dedup.json")

    chunk_size: int = 600
    chunk_overlap: int = 100
    chunk_min_words: int = 20
    enable_summary_augment: bool = True
    embed_summary_augment: bool = True
    summary_max_sentences: int = 3

    top_k: int = 10
    rerank_top_k: int = 5
    enable_rerank: bool = False
    rerank_model: str = "cross-encoder/ms-marco-MiniLM-L6-v2"
    rrf_k: int = 60
    hybrid_weight_dense: float = 0.5
    bm25_backend: str = "qdrant"
    bm25_local_path: str = str(PROJECT_ROOT / "data" / "cache" / "bm25.pkl")
    bm25_k1: float = 1.5
    bm25_b: float = 0.75

    upload_max_bytes: int = 100_000_000
    max_workers: int = 4

    cors_origins: list[str] = ["*"]

    llm_provider: str = "mock"
    llm_model: str = "gpt-4o-mini"
    llm_base_url: str | None = None
    llm_api_key: str | None = None
    llm_temperature: float = 0.2
    llm_max_tokens: int = 1024
    llm_timeout_seconds: int = 120
    llm_max_retries: int = 3
    llm_mock_response: str = ""
    llm_json_instruction: bool = True

    generation_top_k: int = 5
    generation_max_sessions: int = 1000
    conversation_max_turns: int = 20
    conversation_max_chars: int = 12000
    num_candidate_responses: int = 1

    enable_citation_verification: bool = True
    enable_hallucination_detection: bool = True
    enable_confidence_scoring: bool = True
    enable_llm_verification: bool = False
    evidence_min_overlap: float = 0.15
    evidence_contradiction_threshold: float = 0.6
    unsupported_claim_threshold: float = 0.25

    @field_validator("bm25_backend")
    @classmethod
    def _validate_bm25_backend(cls, value: str) -> str:
        if value not in {"qdrant", "local"}:
            raise ValueError("bm25_backend must be 'qdrant' or 'local'")
        return value

    @field_validator("llm_provider")
    @classmethod
    def _validate_llm_provider(cls, value: str) -> str:
        if value.lower() not in {"claude", "openai", "gemini", "llama", "mock"}:
            raise ValueError("llm_provider must be one of 'claude', 'openai', 'gemini', 'llama', 'mock'")
        return value.lower()

    @field_validator("hybrid_weight_dense")
    @classmethod
    def _validate_dense_weight(cls, value: float) -> float:
        if not 0.0 <= value <= 1.0:
            raise ValueError("hybrid_weight_dense must be within [0, 1]")
        return value
