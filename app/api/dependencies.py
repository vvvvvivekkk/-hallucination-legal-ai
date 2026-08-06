from __future__ import annotations

from functools import lru_cache

from fastapi import Depends

from ..config import Settings
from ..core.logger import get_logger
from ..generation.llm import LLMConfig, build_llm
from ..generation.memory import ConversationMemory
from ..generation.pipeline import GenerationPipeline
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
def get_store() -> QdrantStore:
    settings = get_settings()
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
def get_local_bm25() -> LocalBm25Index:
    settings = get_settings()
    index = LocalBm25Index(
        k1=settings.bm25_k1,
        b=settings.bm25_b,
        store_path=settings.bm25_local_path,
        logger=logger,
    )
    index.load()
    return index


@lru_cache(maxsize=1)
def get_embedder() -> Embedder:
    settings = get_settings()
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
    store: QdrantStore = Depends(get_store),
    embedder: Embedder = Depends(get_embedder),
    local_bm25: LocalBm25Index = Depends(get_local_bm25),
) -> IngestionPipeline:
    settings = get_settings()
    return IngestionPipeline(
        settings=settings,
        store=store,
        embedder=embedder,
        local_bm25=local_bm25 if settings.bm25_backend == "local" else None,
        logger=logger,
    )


@lru_cache(maxsize=1)
def get_llm():
    settings = get_settings()
    config = LLMConfig(
        provider=settings.llm_provider,
        model=settings.llm_model,
        base_url=settings.llm_base_url,
        api_key=settings.llm_api_key,
        temperature=settings.llm_temperature,
        max_tokens=settings.llm_max_tokens,
        timeout_seconds=settings.llm_timeout_seconds,
        max_retries=settings.llm_max_retries,
        mock_response=settings.llm_mock_response,
        json_instruction=settings.llm_json_instruction,
    )
    return build_llm(config, logger)


@lru_cache(maxsize=1)
def get_memory() -> ConversationMemory:
    settings = get_settings()
    return ConversationMemory(
        max_turns=settings.conversation_max_turns,
        max_chars=settings.conversation_max_chars,
        max_sessions=settings.generation_max_sessions,
    )


def get_generation(
    settings: Settings = Depends(get_settings),
    retriever: HybridRetriever = Depends(get_retriever),
    llm=Depends(get_llm),
    memory: ConversationMemory = Depends(get_memory),
) -> GenerationPipeline:
    return GenerationPipeline(
        settings=settings,
        retriever=retriever,
        llm=llm,
        memory=memory,
        logger=logger,
    )
