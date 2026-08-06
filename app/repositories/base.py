from __future__ import annotations

from datetime import datetime
from typing import Any, Protocol


class UserRecord(Protocol):
    id: str
    email: str
    full_name: str
    password_hash: str
    role: str
    is_active: bool
    avatar_url: str | None
    last_login_at: datetime | None
    preferences: dict


class SessionRecord(Protocol):
    id: str
    user_id: str
    token_hash: str
    user_agent: str | None
    ip_address: str | None
    expires_at: datetime
    revoked_at: datetime | None
    replaced_by: str | None


class ConversationRecord(Protocol):
    id: str
    user_id: str
    title: str
    is_pinned: bool
    model: str | None
    collection: str | None
    metadata_: dict
    last_message_at: datetime | None
    created_at: datetime
    updated_at: datetime


class MessageRecord(Protocol):
    id: str
    conversation_id: str
    role: str
    content: str
    sources: list
    citations: list
    verification: dict | None
    hallucination: dict | None
    confidence: dict | None
    quality_score: float
    latency_ms: int
    tokens: int
    created_at: datetime


class ShareRecord(Protocol):
    id: str
    conversation_id: str
    slug: str
    expires_at: datetime | None
    is_public: bool


class UserRepository(Protocol):
    async def get(self, user_id: str) -> UserRecord | None: ...
    async def get_by_email(self, email: str) -> UserRecord | None: ...
    async def create(
        self,
        *,
        email: str,
        full_name: str,
        password_hash: str,
        role: str = "user",
        is_active: bool = True,
    ) -> UserRecord: ...
    async def update(self, user: UserRecord, **fields: Any) -> UserRecord: ...
    async def list(
        self, *, offset: int = 0, limit: int = 50, search: str | None = None
    ) -> tuple[list[UserRecord], int]: ...
    async def list_all(self) -> list[UserRecord]: ...
    async def count(self) -> int: ...
    async def touch_login(self, user: UserRecord) -> None: ...


class SessionRepository(Protocol):
    async def get(self, session_id: str) -> SessionRecord | None: ...
    async def get_by_hash(self, token_hash: str) -> SessionRecord | None: ...
    async def create(
        self,
        *,
        user_id: str,
        token_hash: str,
        user_agent: str | None,
        ip_address: str | None,
        expires_at: datetime,
    ) -> SessionRecord: ...
    async def revoke(self, session: SessionRecord) -> None: ...
    async def revoke_all_for_user(self, user_id: str) -> None: ...
    async def mark_replaced(self, session: SessionRecord, replacement_hash: str) -> None: ...


class ConversationRepository(Protocol):
    async def create(
        self, *, user_id: str, title: str, model: str | None, collection: str | None
    ) -> ConversationRecord: ...
    async def get(self, conversation_id: str, user_id: str) -> ConversationRecord | None: ...
    async def get_any(self, conversation_id: str) -> ConversationRecord | None: ...
    async def list(
        self,
        *,
        user_id: str,
        offset: int = 0,
        limit: int = 50,
        search: str | None = None,
        pinned_only: bool = False,
    ) -> tuple[list[ConversationRecord], int]: ...
    async def rename(self, conversation: ConversationRecord, title: str) -> ConversationRecord: ...
    async def set_pinned(self, conversation: ConversationRecord, pinned: bool) -> ConversationRecord: ...
    async def delete(self, conversation_id: str, user_id: str) -> bool: ...
    async def touch_message(self, conversation: ConversationRecord, at: datetime) -> None: ...
    async def count(self) -> int: ...


class MessageRepository(Protocol):
    async def add(
        self,
        *,
        conversation_id: str,
        role: str,
        content: str,
        sources: list | None = None,
        citations: list | None = None,
        verification: dict | None = None,
        hallucination: dict | None = None,
        confidence: dict | None = None,
        quality_score: float = 0.0,
        latency_ms: int = 0,
        tokens: int = 0,
    ) -> MessageRecord: ...
    async def list_for_conversation(self, conversation_id: str) -> list[MessageRecord]: ...
    async def count(self) -> int: ...


class ShareRepository(Protocol):
    async def create(
        self, *, conversation_id: str, slug: str, expires_at: datetime | None
    ) -> ShareRecord: ...
    async def get_by_slug(self, slug: str) -> ShareRecord | None: ...
    async def get_for_conversation(self, conversation_id: str) -> ShareRecord | None: ...
    async def revoke(self, share: ShareRecord) -> None: ...
