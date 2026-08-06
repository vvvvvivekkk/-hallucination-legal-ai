from __future__ import annotations

import os

os.environ.setdefault("LOG_LEVEL", "WARNING")

from pathlib import Path
from typing import Any

import numpy as np
import pytest
from fastapi.testclient import TestClient

from app.api import dependencies
from app.config import Settings
from app.ingestion.pipeline import IngestionPipeline, IngestTask
from app.main import app
from app.retrieval.base import RankedResult
from app.retrieval.hybrid import HybridRetriever
from app.services.jobs import JobManager


class FakeStore:
    def __init__(self) -> None:
        self.results: list[RankedResult] = []

    def ping(self) -> bool:
        return True

    def ensure_collection(self, collection: str | None = None) -> bool:
        return True

    def collection_exists(self, collection: str | None = None) -> bool:
        return True

    def collection_info(self, collection: str | None = None) -> dict[str, Any]:
        return {"name": collection or "test", "status": "green", "points": 0}

    def scroll_all(self, collection: str | None = None, page_size: int = 1000) -> list[tuple[str, dict]]:
        return []

    def semantic_search(
        self,
        query_vector: np.ndarray,
        top_k: int = 10,
        conditions: dict[str, Any] | None = None,
        score_threshold: float | None = None,
    ) -> list[RankedResult]:
        return self.results[:top_k]

    def search(
        self,
        query: str,
        top_k: int = 10,
        conditions: dict[str, Any] | None = None,
    ) -> list[RankedResult]:
        return self.results[:top_k]


class FakeStoreWithUpsert(FakeStore):
    def __init__(self) -> None:
        super().__init__()
        self.upsert_calls = 0
        self.collections: set[str] = set()

    def ensure_collection(self, collection: str | None = None) -> bool:
        self.collections.add(collection or "test")
        return True

    def collection_exists(self, collection: str | None = None) -> bool:
        return (collection or "test") in self.collections

    def upsert_chunks(
        self,
        chunks: list[Any],
        collection: str | None = None,
        embeddings: np.ndarray | None = None,
        batch_size: int = 256,
    ) -> None:
        self.upsert_calls += 1

    def delete_collection(self, collection: str | None = None) -> None:
        self.collections.discard(collection or "test")


class FakeEmbedder:
    def embed_query(self, text: str) -> np.ndarray:
        return np.zeros(64, dtype=np.float32)

    def embed_texts(self, texts: list[str]) -> np.ndarray:
        return np.zeros((len(texts), 64), dtype=np.float32)

    def embed_chunks(self, chunks: list[Any], use_augmented: bool = True) -> np.ndarray:
        return np.zeros((len(chunks), 64), dtype=np.float32)


class FakePipeline:
    def run(self, job_id: str, task: IngestTask, jobs: JobManager) -> dict[str, Any]:
        jobs.update(job_id, status="completed", progress=1.0, message="done", stats={})
        return {"files_scanned": 0}

    def index(self, job_id: str, task: Any, jobs: JobManager) -> dict[str, Any]:
        jobs.update(job_id, status="completed", progress=1.0, message="done", stats={})
        return {}

    def reindex(self, job_id: str, task: Any, jobs: JobManager) -> dict[str, Any]:
        jobs.update(job_id, status="completed", progress=1.0, message="done", stats={})
        return {}


def fake_settings() -> Settings:
    return Settings()


def _make_retriever(store: FakeStore, embedder: FakeEmbedder) -> HybridRetriever:
    return HybridRetriever(
        dense_searcher=store,
        lexical_searcher=store,
        embedder=embedder,
        top_k=10,
        rrf_k=60,
        dense_weight=0.5,
    )


@pytest.fixture
def test_settings() -> Settings:
    return fake_settings()


@pytest.fixture
def fake_store() -> FakeStore:
    return FakeStore()


@pytest.fixture
def fake_embedder() -> FakeEmbedder:
    return FakeEmbedder()


@pytest.fixture
def client(fake_store: FakeStore, fake_embedder: FakeEmbedder):
    jobs = JobManager()
    app.dependency_overrides.clear()
    app.dependency_overrides[dependencies.get_settings] = fake_settings
    app.dependency_overrides[dependencies.get_store] = lambda: fake_store
    app.dependency_overrides[dependencies.get_embedder] = lambda: fake_embedder
    app.dependency_overrides[dependencies.get_retriever] = lambda: _make_retriever(
        fake_store, fake_embedder
    )
    app.dependency_overrides[dependencies.get_jobs] = lambda: jobs
    app.dependency_overrides[dependencies.get_pipeline] = lambda: FakePipeline()
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def project_root() -> Path:
    return Path(__file__).resolve().parent.parent
