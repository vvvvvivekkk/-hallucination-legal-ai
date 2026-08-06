from __future__ import annotations

import time

from fastapi import APIRouter, Depends
from starlette.concurrency import run_in_threadpool

from ...config import Settings
from ...retrieval.hybrid import HybridRetriever
from ..dependencies import get_retriever, get_settings
from ..schemas import SearchHit, SearchRequest, SearchResponse

router = APIRouter(prefix="/api", tags=["search"])

_EXCLUDED_PAYLOAD_FIELDS = {"chunk_text", "embedded_text", "summary", "chunk_id", "doc_id"}


@router.post("/search", response_model=SearchResponse)
async def search(
    request: SearchRequest,
    retriever: HybridRetriever = Depends(get_retriever),
    settings: Settings = Depends(get_settings),
) -> SearchResponse:
    started = time.monotonic()
    conditions = request.filters.to_conditions() if request.filters else None
    results = await run_in_threadpool(
        retriever.search,
        request.query,
        request.top_k or settings.top_k,
        conditions,
        request.dense_weight,
    )

    hits: list[SearchHit] = []
    for result in results:
        payload = result.payload or {}
        hits.append(
            SearchHit(
                chunk_id=result.chunk_id,
                doc_id=payload.get("doc_id", ""),
                score=result.score,
                text=payload.get("chunk_text", ""),
                summary=payload.get("summary"),
                metadata={
                    key: value
                    for key, value in payload.items()
                    if key not in _EXCLUDED_PAYLOAD_FIELDS
                },
                dense_score=result.dense_score,
                lexical_score=result.lexical_score,
            )
        )

    elapsed = int((time.monotonic() - started) * 1000)
    return SearchResponse(
        query=request.query,
        collection=request.collection or settings.qdrant_collection,
        total=len(hits),
        elapsed_ms=elapsed,
        results=hits,
    )
