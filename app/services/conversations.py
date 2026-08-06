from __future__ import annotations

import secrets
from datetime import datetime, timedelta
from typing import Any

from ..core.exceptions import AuthorizationError, NotFoundError, ValidationError
from ..db.models import utcnow
from ..repositories.base import (
    ConversationRepository,
    MessageRepository,
    ShareRepository,
)


def _iso(value) -> str | None:
    if value is None:
        return None
    return value.isoformat() if hasattr(value, "isoformat") else str(value)


def serialize_conversation(record: Any) -> dict[str, Any]:
    return {
        "id": record.id,
        "title": record.title,
        "is_pinned": bool(getattr(record, "is_pinned", False)),
        "model": getattr(record, "model", None),
        "collection": getattr(record, "collection", None),
        "created_at": _iso(record.created_at),
        "updated_at": _iso(record.updated_at),
        "last_message_at": _iso(getattr(record, "last_message_at", None)),
    }


def serialize_message(record: Any) -> dict[str, Any]:
    return {
        "id": record.id,
        "role": record.role,
        "content": record.content,
        "sources": getattr(record, "sources", []) or [],
        "citations": getattr(record, "citations", []) or [],
        "verification": getattr(record, "verification", None),
        "hallucination": getattr(record, "hallucination", None),
        "confidence": getattr(record, "confidence", None),
        "quality_score": float(getattr(record, "quality_score", 0.0) or 0.0),
        "latency_ms": int(getattr(record, "latency_ms", 0) or 0),
        "tokens": int(getattr(record, "tokens", 0) or 0),
        "created_at": _iso(record.created_at),
    }


class ConversationService:
    def __init__(
        self,
        conversations: ConversationRepository,
        messages: MessageRepository,
        shares: ShareRepository,
    ) -> None:
        self._conversations = conversations
        self._messages = messages
        self._shares = shares

    async def create(
        self,
        user_id: str,
        title: str = "New chat",
        model: str | None = None,
        collection: str | None = None,
    ) -> dict[str, Any]:
        record = await self._conversations.create(
            user_id=user_id,
            title=(title or "New chat").strip()[:200] or "New chat",
            model=model,
            collection=collection,
        )
        return serialize_conversation(record)

    async def list(
        self,
        user_id: str,
        offset: int = 0,
        limit: int = 50,
        search: str | None = None,
        pinned_only: bool = False,
    ) -> dict[str, Any]:
        records, total = await self._conversations.list(
            user_id=user_id,
            offset=offset,
            limit=limit,
            search=search,
            pinned_only=pinned_only,
        )
        return {
            "items": [serialize_conversation(record) for record in records],
            "total": total,
            "offset": offset,
            "limit": limit,
        }

    async def get(self, conversation_id: str, user_id: str) -> dict[str, Any]:
        record = await self._conversations.get(conversation_id, user_id)
        if record is None:
            raise NotFoundError("conversation not found")
        messages = await self._messages.list_for_conversation(conversation_id)
        return {
            **serialize_conversation(record),
            "messages": [serialize_message(message) for message in messages],
        }

    async def update(
        self,
        conversation_id: str,
        user_id: str,
        title: str | None = None,
        is_pinned: bool | None = None,
    ) -> dict[str, Any]:
        record = await self._conversations.get(conversation_id, user_id)
        if record is None:
            raise NotFoundError("conversation not found")
        if title is not None:
            if not title.strip():
                raise ValidationError("title must not be empty")
            await self._conversations.rename(record, title.strip()[:200])
        if is_pinned is not None:
            await self._conversations.set_pinned(record, is_pinned)
        return serialize_conversation(record)

    async def delete(self, conversation_id: str, user_id: str) -> None:
        deleted = await self._conversations.delete(conversation_id, user_id)
        if not deleted:
            raise NotFoundError("conversation not found")

    async def persist_exchange(
        self,
        *,
        conversation_id: str,
        user_id: str,
        user_message: str,
        assistant_message: str,
        sources: list[dict[str, Any]] | None = None,
        citations: list[dict[str, Any]] | None = None,
        verification: dict[str, Any] | None = None,
        hallucination: dict[str, Any] | None = None,
        confidence: dict[str, Any] | None = None,
        quality_score: float = 0.0,
        latency_ms: int = 0,
        tokens: int = 0,
    ) -> dict[str, Any]:
        record = await self._conversations.get(conversation_id, user_id)
        if record is None:
            record = await self._conversations.create(
                user_id=user_id,
                title=_default_title(user_message),
                model=None,
                collection=None,
            )
        now = utcnow()
        await self._messages.add(
            conversation_id=record.id,
            role="user",
            content=user_message,
        )
        await self._messages.add(
            conversation_id=record.id,
            role="assistant",
            content=assistant_message,
            sources=sources or [],
            citations=citations or [],
            verification=verification,
            hallucination=hallucination,
            confidence=confidence,
            quality_score=quality_score,
            latency_ms=latency_ms,
            tokens=tokens,
        )
        await self._conversations.touch_message(record, now)
        if getattr(record, "title", None) in (None, "New chat"):
            await self._conversations.rename(record, _default_title(user_message))
        return serialize_conversation(record)

    async def share(
        self,
        conversation_id: str,
        user_id: str,
        expires_in_days: int | None = None,
    ) -> dict[str, Any]:
        record = await self._conversations.get(conversation_id, user_id)
        if record is None:
            raise NotFoundError("conversation not found")
        existing = await self._shares.get_for_conversation(conversation_id)
        if existing is not None:
            await self._shares.revoke(existing)
        slug = secrets.token_urlsafe(9)
        expires_at = (
            utcnow() + timedelta(days=expires_in_days) if expires_in_days else None
        )
        share = await self._shares.create(
            conversation_id=conversation_id, slug=slug, expires_at=expires_at
        )
        return {"slug": share.slug, "expires_at": _iso(expires_at)}

    async def revoke_share(self, conversation_id: str, user_id: str) -> None:
        record = await self._conversations.get(conversation_id, user_id)
        if record is None:
            raise NotFoundError("conversation not found")
        share = await self._shares.get_for_conversation(conversation_id)
        if share is not None:
            await self._shares.revoke(share)

    async def public_share(self, slug: str) -> dict[str, Any] | None:
        share = await self._shares.get_by_slug(slug)
        if share is None:
            return None
        if share.expires_at is not None and share.expires_at < utcnow():
            return None
        record = await self._conversations.get_any(share.conversation_id)
        if record is None:
            return None
        messages = await self._messages.list_for_conversation(record.id)
        return {
            "conversation_id": record.id,
            "title": record.title,
            "created_at": _iso(record.created_at),
            "updated_at": _iso(record.updated_at),
            "last_message_at": _iso(getattr(record, "last_message_at", None)),
            "messages": [serialize_message(message) for message in messages],
        }


def _default_title(user_message: str) -> str:
    cleaned = " ".join((user_message or "").split())
    return cleaned[:80] if cleaned else "New chat"


def require_owner(record: Any, user_id: str) -> None:
    if getattr(record, "user_id", None) != user_id:
        raise AuthorizationError("you do not own this resource")
