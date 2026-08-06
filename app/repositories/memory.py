from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any

from ..db.models import utcnow


@dataclass
class MemUser:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    email: str = ""
    full_name: str = ""
    password_hash: str = ""
    role: str = "user"
    is_active: bool = True
    avatar_url: str | None = None
    last_login_at: datetime | None = None
    preferences: dict = field(default_factory=dict)
    created_at: datetime = field(default_factory=utcnow)
    updated_at: datetime = field(default_factory=utcnow)


@dataclass
class MemSession:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str = ""
    token_hash: str = ""
    user_agent: str | None = None
    ip_address: str | None = None
    expires_at: datetime = field(default_factory=lambda: utcnow() + timedelta(days=30))
    revoked_at: datetime | None = None
    replaced_by: str | None = None
    created_at: datetime = field(default_factory=utcnow)
    updated_at: datetime = field(default_factory=utcnow)


@dataclass
class MemConversation:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str = ""
    title: str = "New chat"
    is_pinned: bool = False
    model: str | None = None
    collection: str | None = None
    metadata_: dict = field(default_factory=dict)
    last_message_at: datetime | None = None
    created_at: datetime = field(default_factory=utcnow)
    updated_at: datetime = field(default_factory=utcnow)


@dataclass
class MemMessage:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    conversation_id: str = ""
    role: str = "user"
    content: str = ""
    sources: list = field(default_factory=list)
    citations: list = field(default_factory=list)
    verification: dict | None = None
    hallucination: dict | None = None
    confidence: dict | None = None
    quality_score: float = 0.0
    latency_ms: int = 0
    tokens: int = 0
    created_at: datetime = field(default_factory=utcnow)
    updated_at: datetime = field(default_factory=utcnow)


@dataclass
class MemShare:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    conversation_id: str = ""
    slug: str = ""
    expires_at: datetime | None = None
    is_public: bool = True
    created_at: datetime = field(default_factory=utcnow)
    updated_at: datetime = field(default_factory=utcnow)


class MemoryStore:
    """Thread-safe in-memory repository store used for tests and dev fallback."""

    def __init__(self) -> None:
        self.users: dict[str, MemUser] = {}
        self.sessions: dict[str, MemSession] = {}
        self.conversations: dict[str, MemConversation] = {}
        self.messages: dict[str, list[MemMessage]] = {}
        self.shares: dict[str, MemShare] = {}


class MemoryUserRepository:
    def __init__(self, store: MemoryStore) -> None:
        self._store = store

    async def get(self, user_id: str) -> MemUser | None:
        return self._store.users.get(user_id)

    async def get_by_email(self, email: str) -> MemUser | None:
        for user in self._store.users.values():
            if user.email.lower() == (email or "").lower():
                return user
        return None

    async def create(
        self,
        *,
        email: str,
        full_name: str,
        password_hash: str,
        role: str = "user",
        is_active: bool = True,
    ) -> MemUser:
        user = MemUser(
            email=email,
            full_name=full_name,
            password_hash=password_hash,
            role=role,
            is_active=is_active,
        )
        self._store.users[user.id] = user
        return user

    async def update(self, user: MemUser, **fields: Any) -> MemUser:
        for key, value in fields.items():
            if hasattr(user, key):
                setattr(user, key, value)
        user.updated_at = utcnow()
        return user

    async def list(
        self, *, offset: int = 0, limit: int = 50, search: str | None = None
    ) -> tuple[list[MemUser], int]:
        rows = list(self._store.users.values())
        if search:
            pattern = search.lower()
            rows = [
                user
                for user in rows
                if pattern in user.email.lower() or pattern in user.full_name.lower()
            ]
        rows.sort(key=lambda user: user.created_at, reverse=True)
        return rows[offset : offset + limit], len(rows)

    async def list_all(self) -> list[MemUser]:
        return list(self._store.users.values())

    async def count(self) -> int:
        return len(self._store.users)

    async def touch_login(self, user: MemUser) -> None:
        user.last_login_at = utcnow()


class MemorySessionRepository:
    def __init__(self, store: MemoryStore) -> None:
        self._store = store

    async def get(self, session_id: str) -> MemSession | None:
        return self._store.sessions.get(session_id)

    async def get_by_hash(self, token_hash: str) -> MemSession | None:
        for session in self._store.sessions.values():
            if session.token_hash == token_hash:
                return session
        return None

    async def create(
        self,
        *,
        user_id: str,
        token_hash: str,
        user_agent: str | None,
        ip_address: str | None,
        expires_at: datetime,
    ) -> MemSession:
        session = MemSession(
            user_id=user_id,
            token_hash=token_hash,
            user_agent=user_agent,
            ip_address=ip_address,
            expires_at=expires_at,
        )
        self._store.sessions[session.id] = session
        return session

    async def revoke(self, session: MemSession) -> None:
        session.revoked_at = utcnow()

    async def revoke_all_for_user(self, user_id: str) -> None:
        for key in list(self._store.sessions):
            if self._store.sessions[key].user_id == user_id:
                del self._store.sessions[key]

    async def mark_replaced(self, session: MemSession, replacement_hash: str) -> None:
        session.replaced_by = replacement_hash
        session.revoked_at = utcnow()


class MemoryConversationRepository:
    def __init__(self, store: MemoryStore) -> None:
        self._store = store

    async def create(
        self, *, user_id: str, title: str, model: str | None, collection: str | None
    ) -> MemConversation:
        record = MemConversation(
            user_id=user_id, title=title, model=model, collection=collection
        )
        self._store.conversations[record.id] = record
        return record

    async def get(self, conversation_id: str, user_id: str) -> MemConversation | None:
        record = self._store.conversations.get(conversation_id)
        if record is not None and record.user_id == user_id:
            return record
        return None

    async def get_any(self, conversation_id: str) -> MemConversation | None:
        return self._store.conversations.get(conversation_id)

    async def list(
        self,
        *,
        user_id: str,
        offset: int = 0,
        limit: int = 50,
        search: str | None = None,
        pinned_only: bool = False,
    ) -> tuple[list[MemConversation], int]:
        rows = [
            record
            for record in self._store.conversations.values()
            if record.user_id == user_id
        ]
        if pinned_only:
            rows = [record for record in rows if record.is_pinned]
        if search:
            pattern = search.lower()
            rows = [record for record in rows if pattern in record.title.lower()]
        rows.sort(
            key=lambda record: record.last_message_at or record.created_at,
            reverse=True,
        )
        return rows[offset : offset + limit], len(rows)

    async def rename(self, conversation: MemConversation, title: str) -> MemConversation:
        conversation.title = title
        conversation.updated_at = utcnow()
        return conversation

    async def set_pinned(self, conversation: MemConversation, pinned: bool) -> MemConversation:
        conversation.is_pinned = pinned
        conversation.updated_at = utcnow()
        return conversation

    async def delete(self, conversation_id: str, user_id: str) -> bool:
        record = self._store.conversations.get(conversation_id)
        if record is None or record.user_id != user_id:
            return False
        del self._store.conversations[conversation_id]
        self._store.messages.pop(conversation_id, None)
        return True

    async def touch_message(self, conversation: MemConversation, at: datetime) -> None:
        conversation.last_message_at = at
        conversation.updated_at = utcnow()

    async def count(self) -> int:
        return len(self._store.conversations)


class MemoryMessageRepository:
    def __init__(self, store: MemoryStore) -> None:
        self._store = store

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
    ) -> MemMessage:
        record = MemMessage(
            conversation_id=conversation_id,
            role=role,
            content=content,
            sources=sources or [],
            citations=citations or [],
            verification=verification,
            hallucination=hallucination,
            confidence=confidence,
            quality_score=quality_score,
            latency_ms=latency_ms,
            tokens=tokens,
        )
        self._store.messages.setdefault(conversation_id, []).append(record)
        return record

    async def list_for_conversation(self, conversation_id: str) -> list[MemMessage]:
        return list(self._store.messages.get(conversation_id, []))

    async def count(self) -> int:
        return sum(len(rows) for rows in self._store.messages.values())


class MemoryShareRepository:
    def __init__(self, store: MemoryStore) -> None:
        self._store = store

    async def create(
        self, *, conversation_id: str, slug: str, expires_at: datetime | None
    ) -> MemShare:
        record = MemShare(
            conversation_id=conversation_id, slug=slug, expires_at=expires_at
        )
        self._store.shares[record.id] = record
        return record

    async def get_by_slug(self, slug: str) -> MemShare | None:
        for share in self._store.shares.values():
            if share.slug == slug:
                return share
        return None

    async def get_for_conversation(self, conversation_id: str) -> MemShare | None:
        for share in self._store.shares.values():
            if share.conversation_id == conversation_id:
                return share
        return None

    async def revoke(self, share: MemShare) -> None:
        self._store.shares.pop(share.id, None)
