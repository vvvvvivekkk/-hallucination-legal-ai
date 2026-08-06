from __future__ import annotations

from functools import lru_cache

from fastapi import Depends

from ..config import Settings
from ..core.logger import get_logger
from ..ingestion.embedder import Embedder, EmbeddingCache
from ..ingestion.pipeline import IngestionPipeline
from ..retrieval.bm25 import LocalBm25Index
from ..retrieval.hybrid import HybridRetriever
from ..retrieval.qdrant import QdrantStore
from ..retrieval.reranker import CrossEncoderReranker
from ..services.jobs import JobManager

logger = get_logger(__name__)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


@lru_cache(maxsize=1)
def get_store(settings: Settings = Depends(get_settings)) -> QdrantStore:
    return QdrantStore(
        url=settings.qdrant_url,
        api_key=settings.qdrant_api_key,
        collection=settings.qdrant_collection,
        embedding_dim=settings.embedding_dim,
        timeout=settings.qdrant_timeout_seconds,
        prefer_grpc=settings.qdrant_prefer_grpc,
        max_retries=settings.qdrant_max_retries,
        logger=logger,
    )


@lru_cache(maxsize=1)
def get_local_bm25(settings: Settings = Depends(get_settings)) -> LocalBm25Index:
    index = LocalBm25Index(
        k1=settings.bm25_k1,
        b=settings.bm25_b,
        store_path=settings.bm25_local_path,
        logger=logger,
    )
    index.load()
    return index


@lru_cache(maxsize=1)
def get_embedder(settings: Settings = Depends(get_settings)) -> Embedder:
    cache = EmbeddingCache(settings.embedding_cache_path) if settings.embedding_cache_path else None
    return Embedder(
        model_name=settings.embedding_model,
        device=settings.embedding_device,
        batch_size=settings.embedding_batch_size,
        cache=cache,
        query_prefix=settings.embedding_query_prefix,
        logger=logger,
    )


def get_reranker(settings: Settings = Depends(get_settings)) -> CrossEncoderReranker | None:
    if not settings.enable_rerank:
        return None
    return CrossEncoderReranker(
        model_name=settings.rerank_model,
        device=settings.embedding_device,
        logger=logger,
    )


def get_retriever(
    settings: Settings = Depends(get_settings),
    store: QdrantStore = Depends(get_store),
    local_bm25: LocalBm25Index = Depends(get_local_bm25),
    embedder: Embedder = Depends(get_embedder),
    reranker: CrossEncoderReranker | None = Depends(get_reranker),
) -> HybridRetriever:
    lexical = store if settings.bm25_backend == "qdrant" else local_bm25
    return HybridRetriever(
        dense_searcher=store,
        lexical_searcher=lexical,
        embedder=embedder,
        top_k=settings.top_k,
        rrf_k=settings.rrf_k,
        dense_weight=settings.hybrid_weight_dense,
        reranker=reranker,
        rerank_top_k=settings.rerank_top_k,
        logger=logger,
    )


@lru_cache(maxsize=1)
def get_jobs() -> JobManager:
    return JobManager()


@lru_cache(maxsize=1)
def get_pipeline(
    settings: Settings = Depends(get_settings),
    store: QdrantStore = Depends(get_store),
    embedder: Embedder = Depends(get_embedder),
    local_bm25: LocalBm25Index = Depends(get_local_bm25),
) -> IngestionPipeline:
    return IngestionPipeline(
        settings=settings,
        store=store,
        embedder=embedder,
        local_bm25=local_bm25 if settings.bm25_backend == "local" else None,
        logger=logger,
    )
