from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db.models import (
    ApiUsage,
    Conversation,
    Message,
    RefreshSession,
    SharedLink,
    User,
)


class PostgresUserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, user_id: str) -> User | None:
        return await self._session.get(User, user_id)

    async def get_by_email(self, email: str) -> User | None:
        result = await self._session.execute(
            select(User).where(func.lower(User.email) == email.lower())
        )
        return result.scalar_one_or_none()

    async def create(
        self,
        *,
        email: str,
        full_name: str,
        password_hash: str,
        role: str = "user",
        is_active: bool = True,
    ) -> User:
        user = User(
            email=email,
            full_name=full_name,
            password_hash=password_hash,
            role=role,
            is_active=is_active,
        )
        self._session.add(user)
        await self._session.flush()
        return user

    async def update(self, user: User, **fields: Any) -> User:
        for key, value in fields.items():
            setattr(user, key, value)
        await self._session.flush()
        return user

    async def list(
        self, *, offset: int = 0, limit: int = 50, search: str | None = None
    ) -> tuple[list[User], int]:
        query = select(User)
        count_query = select(func.count(User.id))
        if search:
            pattern = f"%{search}%"
            query = query.where(
                (User.email.ilike(pattern)) | (User.full_name.ilike(pattern))
            )
            count_query = count_query.where(
                (User.email.ilike(pattern)) | (User.full_name.ilike(pattern))
            )
        total = (await self._session.execute(count_query)).scalar_one()
        rows = (
            (
                await self._session.execute(
                    query.order_by(User.created_at.desc()).offset(offset).limit(limit)
                )
            )
            .scalars()
            .all()
        )
        return list(rows), int(total)

    async def list_all(self) -> list[User]:
        rows = (
            await self._session.execute(select(User).order_by(User.created_at.desc()))
        ).scalars()
        return list(rows)

    async def count(self) -> int:
        return int(
            (await self._session.execute(select(func.count(User.id)))).scalar_one()
        )

    async def touch_login(self, user: User) -> None:
        user.last_login_at = datetime.utcnow()
        await self._session.flush()


class PostgresSessionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, session_id: str) -> RefreshSession | None:
        return await self._session.get(RefreshSession, session_id)

    async def get_by_hash(self, token_hash: str) -> RefreshSession | None:
        result = await self._session.execute(
            select(RefreshSession).where(RefreshSession.token_hash == token_hash)
        )
        return result.scalar_one_or_none()

    async def create(
        self,
        *,
        user_id: str,
        token_hash: str,
        user_agent: str | None,
        ip_address: str | None,
        expires_at: datetime,
    ) -> RefreshSession:
        record = RefreshSession(
            user_id=user_id,
            token_hash=token_hash,
            user_agent=user_agent,
            ip_address=ip_address,
            expires_at=expires_at,
        )
        self._session.add(record)
        await self._session.flush()
        return record

    async def revoke(self, session: RefreshSession) -> None:
        session.revoked_at = datetime.utcnow()
        await self._session.flush()

    async def revoke_all_for_user(self, user_id: str) -> None:
        await self._session.execute(
            delete(RefreshSession).where(RefreshSession.user_id == user_id)
        )

    async def mark_replaced(self, session: RefreshSession, replacement_hash: str) -> None:
        session.replaced_by = replacement_hash
        session.revoked_at = datetime.utcnow()
        await self._session.flush()


class PostgresConversationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self, *, user_id: str, title: str, model: str | None, collection: str | None
    ) -> Conversation:
        record = Conversation(
            user_id=user_id, title=title, model=model, collection=collection
        )
        self._session.add(record)
        await self._session.flush()
        return record

    async def get(self, conversation_id: str, user_id: str) -> Conversation | None:
        result = await self._session.execute(
            select(Conversation).where(
                Conversation.id == conversation_id,
                Conversation.user_id == user_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_any(self, conversation_id: str) -> Conversation | None:
        return await self._session.get(Conversation, conversation_id)

    async def list(
        self,
        *,
        user_id: str,
        offset: int = 0,
        limit: int = 50,
        search: str | None = None,
        pinned_only: bool = False,
    ) -> tuple[list[Conversation], int]:
        query = select(Conversation).where(Conversation.user_id == user_id)
        count_query = select(func.count(Conversation.id)).where(
            Conversation.user_id == user_id
        )
        if pinned_only:
            query = query.where(Conversation.is_pinned.is_(True))
            count_query = count_query.where(Conversation.is_pinned.is_(True))
        if search:
            pattern = f"%{search}%"
            query = query.where(Conversation.title.ilike(pattern))
            count_query = count_query.where(Conversation.title.ilike(pattern))
        total = (await self._session.execute(count_query)).scalar_one()
        rows = (
            (
                await self._session.execute(
                    query.order_by(Conversation.last_message_at.desc())
                    .offset(offset)
                    .limit(limit)
                )
            )
            .scalars()
            .all()
        )
        return list(rows), int(total)

    async def rename(self, conversation: Conversation, title: str) -> Conversation:
        conversation.title = title
        await self._session.flush()
        return conversation

    async def set_pinned(
        self, conversation: Conversation, pinned: bool
    ) -> Conversation:
        conversation.is_pinned = pinned
        await self._session.flush()
        return conversation

    async def delete(self, conversation_id: str, user_id: str) -> bool:
        result = await self._session.execute(
            delete(Conversation).where(
                Conversation.id == conversation_id,
                Conversation.user_id == user_id,
            )
        )
        return result.rowcount > 0

    async def touch_message(self, conversation: Conversation, at: datetime) -> None:
        conversation.last_message_at = at
        await self._session.flush()

    async def count(self) -> int:
        return int(
            (
                await self._session.execute(
                    select(func.count(Conversation.id))
                )
            ).scalar_one()
        )


class PostgresMessageRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

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
    ) -> Message:
        record = Message(
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
        self._session.add(record)
        await self._session.flush()
        return record

    async def list_for_conversation(self, conversation_id: str) -> list[Message]:
        result = await self._session.execute(
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at.asc())
        )
        return list(result.scalars().all())

    async def count(self) -> int:
        return int(
            (await self._session.execute(select(func.count(Message.id)))).scalar_one()
        )


class PostgresShareRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        *,
        conversation_id: str,
        slug: str,
        expires_at: datetime | None,
    ) -> SharedLink:
        record = SharedLink(
            conversation_id=conversation_id, slug=slug, expires_at=expires_at
        )
        self._session.add(record)
        await self._session.flush()
        return record

    async def get_by_slug(self, slug: str) -> SharedLink | None:
        result = await self._session.execute(
            select(SharedLink).where(SharedLink.slug == slug)
        )
        return result.scalar_one_or_none()

    async def get_for_conversation(self, conversation_id: str) -> SharedLink | None:
        result = await self._session.execute(
            select(SharedLink).where(SharedLink.conversation_id == conversation_id)
        )
        return result.scalar_one_or_none()

    async def revoke(self, share: SharedLink) -> None:
        await self._session.delete(share)
        await self._session.flush()


class PostgresUsageRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def record(
        self,
        *,
        user_id: str | None,
        endpoint: str,
        method: str,
        status_code: int,
        latency_ms: int,
        provider: str | None = None,
        model: str | None = None,
        tokens: int = 0,
        error: str | None = None,
        ip_address: str | None = None,
    ) -> ApiUsage:
        record = ApiUsage(
            user_id=user_id,
            endpoint=endpoint,
            method=method,
            status_code=status_code,
            latency_ms=latency_ms,
            provider=provider,
            model=model,
            tokens=tokens,
            error=error,
            ip_address=ip_address,
        )
        self._session.add(record)
        await self._session.flush()
        return record

    async def stats(self, user_id: str | None = None) -> dict[str, Any]:
        base = select(ApiUsage)
        if user_id is not None:
            base = base.where(ApiUsage.user_id == user_id)
        total = (await self._session.execute(select(func.count()).select_from(base))).scalar_one()
        errors = (
            await self._session.execute(
                select(func.count()).select_from(base).where(ApiUsage.status_code >= 400)
            )
        ).scalar_one()
        return {"total_requests": int(total), "error_requests": int(errors)}
