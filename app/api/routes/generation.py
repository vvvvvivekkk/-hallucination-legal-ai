from __future__ import annotations

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from ...config import Settings
from ...core.exceptions import ValidationError
from ...generation.pipeline import GenerationPipeline
from ..dependencies import get_generation, get_settings
from ..schemas import (
    ChatRequest,
    ChatResponse,
    CitationsRequest,
    CitationsResponse,
    ConfidenceRequest,
    ConfidenceResponse,
    HallucinationRequest,
    HallucinationResponse,
    QueryRequest,
    QueryResponse,
    VerifiedResponseModel,
    VerifyRequest,
    VerifyResponse,
)

router = APIRouter(prefix="/api", tags=["generation"])


def _filters(request) -> dict | None:
    return request.filters.to_conditions() if request.filters else None


@router.post("/query", response_model=QueryResponse)
async def query(
    request: QueryRequest,
    pipeline: GenerationPipeline = Depends(get_generation),
) -> QueryResponse:
    result = await pipeline.generate(
        request.query,
        session_id=request.session_id,
        filters=_filters(request),
        top_k=request.top_k,
        num_responses=request.num_responses or 1,
    )
    return QueryResponse(
        session_id=result.session_id,
        result=VerifiedResponseModel(**result.to_dict()),
    )


@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    pipeline: GenerationPipeline = Depends(get_generation),
) -> ChatResponse | StreamingResponse:
    if request.stream:
        if (request.num_responses or 1) > 1:
            raise ValidationError("streaming cannot be combined with num_responses greater than 1")
        return StreamingResponse(
            pipeline.stream(
                request.query,
                session_id=request.session_id,
                filters=_filters(request),
                top_k=request.top_k,
            ),
            media_type="application/x-ndjson",
        )
    result = await pipeline.generate(
        request.query,
        session_id=request.session_id,
        filters=_filters(request),
        top_k=request.top_k,
        num_responses=request.num_responses or 1,
        store_history=request.store_history,
    )
    return ChatResponse(
        session_id=result.session_id,
        result=VerifiedResponseModel(**result.to_dict()),
    )


@router.post("/verify", response_model=VerifyResponse)
async def verify(
    request: VerifyRequest,
    pipeline: GenerationPipeline = Depends(get_generation),
) -> VerifyResponse:
    result = await pipeline.verify(
        request.query,
        request.answer,
        context=request.context,
        top_k=request.top_k,
        filters=_filters(request),
    )
    return VerifyResponse(result=VerifiedResponseModel(**result.to_dict()))


@router.post("/citations", response_model=CitationsResponse)
async def citations(
    request: CitationsRequest,
    pipeline: GenerationPipeline = Depends(get_generation),
) -> CitationsResponse:
    data = await pipeline.citations(
        request.query,
        request.answer,
        context=request.context,
        top_k=request.top_k,
        filters=_filters(request),
    )
    return CitationsResponse(**data)


@router.post("/hallucination", response_model=HallucinationResponse)
async def hallucination(
    request: HallucinationRequest,
    pipeline: GenerationPipeline = Depends(get_generation),
) -> HallucinationResponse:
    report = await pipeline.hallucination(
        request.query,
        request.answer,
        context=request.context,
        top_k=request.top_k,
        filters=_filters(request),
    )
    return HallucinationResponse(
        query=request.query,
        answer=request.answer,
        hallucination=report.to_dict(),
    )


@router.post("/confidence", response_model=ConfidenceResponse)
async def confidence(
    request: ConfidenceRequest,
    pipeline: GenerationPipeline = Depends(get_generation),
) -> ConfidenceResponse:
    data = await pipeline.confidence(
        request.query,
        request.answer,
        context=request.context,
        top_k=request.top_k,
        filters=_filters(request),
    )
    return ConfidenceResponse(**data)
