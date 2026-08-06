from __future__ import annotations

import asyncio
import json
import logging
import time
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, Request
from fastapi.responses import StreamingResponse

from ...config import Settings
from ...core.exceptions import ValidationError
from ...core.metrics import LLM_REQUESTS_TOTAL, RETRIEVAL_REQUESTS_TOTAL
from ...core.ratelimit import RateLimiter
from ...generation.pipeline import GenerationPipeline
from ...services.conversations import ConversationService
from ..dependencies import get_generation, get_settings
from ..schemas import ChatMessageModel, ConversationModel
from ..security_deps import (
    get_conversation_repo,
    get_current_user,
    get_message_repo,
    get_rate_limiter,
    get_share_repo,
)

logger = logging.getLogger("app.chat")

router = APIRouter(prefix="/api/conversations/chat", tags=["chat"])


def _service(
    conversations=Depends(get_conversation_repo),
    messages=Depends(get_message_repo),
    shares=Depends(get_share_repo),
) -> ConversationService:
    return ConversationService(conversations, messages, shares)


def _assistant_event(result: Any) -> dict[str, Any]:
    data = result.to_dict() if hasattr(result, "to_dict") else result
    confidence = data.get("confidence") or {}
    return {
        "id": None,
        "role": "assistant",
        "content": data.get("answer", ""),
        "sources": data.get("sources", []),
        "citations": data.get("citations", []),
        "verification": data.get("verification"),
        "hallucination": data.get("hallucination"),
        "confidence": confidence,
        "quality_score": round(float(confidence.get("overall", 0.0) or 0.0), 4),
        "latency_ms": int(data.get("elapsed_ms", 0) or 0),
        "tokens": 0,
        "created_at": None,
        "streaming": False,
    }


async def _persist_exchange(
    service: ConversationService,
    user_id: str,
    conversation_id: str,
    user_message: str,
    data: dict[str, Any],
    elapsed_ms: int,
) -> None:
    try:
        confidence = data.get("confidence") or {}
        await service.persist_exchange(
            conversation_id=conversation_id,
            user_id=user_id,
            user_message=user_message,
            assistant_message=data.get("answer", ""),
            sources=data.get("sources") or [],
            citations=data.get("citations") or [],
            verification=data.get("verification"),
            hallucination=data.get("hallucination"),
            confidence=confidence,
            quality_score=round(float(confidence.get("overall", 0.0) or 0.0), 4),
            latency_ms=elapsed_ms,
            tokens=0,
        )
    except Exception:
        logger.exception("failed to persist chat exchange")


async def _ensure_conversation(
    service: ConversationService,
    user_id: str,
    conversation_id: str | None,
    message: str,
) -> str:
    if conversation_id:
        return conversation_id
    record = await service.create(user_id, title=message[:80] or "New chat")
    return record["id"]


async def _run_pipeline(
    pipeline: GenerationPipeline, message: str, conversation_id: str
) -> Any:
    RETRIEVAL_REQUESTS_TOTAL.labels(backend="hybrid").inc()
    provider = getattr(getattr(pipeline, "_llm", None), "provider", "unknown")
    model = getattr(getattr(pipeline, "_llm", None), "model", "unknown")
    LLM_REQUESTS_TOTAL.labels(provider=provider, model=model).inc()
    return await pipeline.generate(
        message, session_id=conversation_id, store_history=False
    )


@router.post("", response_model=ChatMessageModel)
async def chat(
    request: Request,
    body: dict[str, Any],
    background: BackgroundTasks,
    pipeline: GenerationPipeline = Depends(get_generation),
    service: ConversationService = Depends(_service),
    user: Any = Depends(get_current_user),
    limiter: RateLimiter = Depends(get_rate_limiter),
    settings: Settings = Depends(get_settings),
) -> ChatMessageModel:
    message = (body.get("message") or "").strip()
    if not message:
        raise ValidationError("message must not be empty")
    if settings.rate_limit_enabled:
        limiter.check(
            f"chat:{user.id}",
            settings.rate_limit_requests,
            settings.rate_limit_window_seconds,
        )
    conversation_id = await _ensure_conversation(service, user.id, body.get("conversation_id"), message)

    started = time.monotonic()
    result = await _run_pipeline(pipeline, message, conversation_id)
    elapsed = int((time.monotonic() - started) * 1000)

    background.add_task(
        _persist_exchange,
        service,
        user.id,
        conversation_id,
        message,
        result.to_dict(),
        elapsed,
    )
    return ChatMessageModel(
        conversation_id=conversation_id, **_assistant_event(result)
    )


@router.post("/stream")
async def chat_stream(
    request: Request,
    body: dict[str, Any],
    background: BackgroundTasks,
    pipeline: GenerationPipeline = Depends(get_generation),
    service: ConversationService = Depends(_service),
    user: Any = Depends(get_current_user),
    limiter: RateLimiter = Depends(get_rate_limiter),
    settings: Settings = Depends(get_settings),
) -> StreamingResponse:
    message = (body.get("message") or "").strip()
    if not message:
        raise ValidationError("message must not be empty")
    if settings.rate_limit_enabled:
        limiter.check(
            f"chat:{user.id}",
            settings.rate_limit_requests,
            settings.rate_limit_window_seconds,
        )
    conversation_id = await _ensure_conversation(service, user.id, body.get("conversation_id"), message)

    RETRIEVAL_REQUESTS_TOTAL.labels(backend="hybrid").inc()
    provider = getattr(getattr(pipeline, "_llm", None), "provider", "unknown")
    model = getattr(getattr(pipeline, "_llm", None), "model", "unknown")
    LLM_REQUESTS_TOTAL.labels(provider=provider, model=model).inc()

    async def event_stream():
        started = time.monotonic()
        final: dict[str, Any] | None = None
        try:
            async for chunk in pipeline.stream(message, session_id=None):
                data = json.loads(chunk)
                if data.get("type") == "result":
                    final = data.get("result") or {}
                    event = _assistant_event(final)
                    yield json.dumps({"type": "result", "result": event}, ensure_ascii=False) + "\n"
                else:
                    yield chunk
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("streaming failed")
            yield json.dumps({"type": "error", "error": "streaming failed"}, ensure_ascii=False) + "\n"
        finally:
            if final is not None:
                elapsed = int((time.monotonic() - started) * 1000)
                background.add_task(
                    _persist_exchange,
                    service,
                    user.id,
                    conversation_id,
                    message,
                    final,
                    elapsed,
                )

    return StreamingResponse(event_stream(), media_type="application/x-ndjson")
