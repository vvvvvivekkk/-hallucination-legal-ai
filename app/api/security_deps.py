from __future__ import annotations

from typing import Any

from fastapi import Depends, Request

from ..config import Settings
from ..core.exceptions import AuthenticationError, AuthorizationError
from ..core.ratelimit import RateLimiter
from ..core.security import decode_access_token
from ..db.base import get_session_factory
from ..repositories.base import (
    ConversationRepository,
    MessageRepository,
    SessionRepository,
    ShareRepository,
    UserRepository,
)
from ..repositories.memory import (
    MemoryConversationRepository,
    MemoryMessageRepository,
    MemorySessionRepository,
    MemoryShareRepository,
    MemoryStore,
    MemoryUserRepository,
)
from ..repositories.postgres import (
    PostgresConversationRepository,
    PostgresMessageRepository,
    PostgresSessionRepository,
    PostgresShareRepository,
    PostgresUserRepository,
)
from .dependencies import get_settings

_memory_store: MemoryStore | None = None
_memory_limiter: RateLimiter | None = None


def get_memory_store() -> MemoryStore:
    global _memory_store
    if _memory_store is None:
        _memory_store = MemoryStore()
    return _memory_store


async def get_db_session():
    settings = get_settings()
    if not settings.database_url:
        yield None
        return
    factory = get_session_factory(settings)
    async with factory() as session:
        yield session


def get_user_repo(session: Any = Depends(get_db_session)) -> UserRepository:
    if session is None:
        return MemoryUserRepository(get_memory_store())
    return PostgresUserRepository(session)


def get_session_repo(session: Any = Depends(get_db_session)) -> SessionRepository:
    if session is None:
        return MemorySessionRepository(get_memory_store())
    return PostgresSessionRepository(session)


def get_conversation_repo(
    session: Any = Depends(get_db_session),
) -> ConversationRepository:
    if session is None:
        return MemoryConversationRepository(get_memory_store())
    return PostgresConversationRepository(session)


def get_message_repo(session: Any = Depends(get_db_session)) -> MessageRepository:
    if session is None:
        return MemoryMessageRepository(get_memory_store())
    return PostgresMessageRepository(session)


def get_share_repo(session: Any = Depends(get_db_session)) -> ShareRepository:
    if session is None:
        return MemoryShareRepository(get_memory_store())
    return PostgresShareRepository(session)


def get_redis_client():
    settings = get_settings()
    if not settings.redis_url:
        return None
    try:
        import redis.asyncio as aioredis

        client = aioredis.from_url(
            settings.redis_url,
            socket_timeout=settings.redis_socket_timeout,
            decode_responses=True,
        )
        return client
    except Exception:
        return None


def get_rate_limiter(
    settings: Settings = Depends(get_settings),
    redis_client: Any = Depends(get_redis_client),
) -> RateLimiter:
    global _memory_limiter
    if redis_client is None:
        if _memory_limiter is None:
            _memory_limiter = RateLimiter(
                redis_client=None,
                prefix=settings.redis_prefix + "rl:",
                enabled=settings.rate_limit_enabled,
            )
        return _memory_limiter
    return RateLimiter(
        redis_client=redis_client,
        prefix=settings.redis_prefix + "rl:",
        enabled=settings.rate_limit_enabled,
    )


def get_client_ip(request: Request) -> str | None:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else None


def get_user_agent(request: Request) -> str | None:
    return request.headers.get("user-agent")


def _extract_bearer(request: Request) -> str | None:
    authorization = request.headers.get("authorization", "")
    if authorization.lower().startswith("bearer "):
        return authorization[7:].strip()
    return None


async def get_current_user(
    request: Request,
    settings: Settings = Depends(get_settings),
    users: UserRepository = Depends(get_user_repo),
) -> Any:
    token = _extract_bearer(request)
    if token is None:
        token = request.cookies.get(settings.access_token_cookie_name)
    if not token:
        raise AuthenticationError("authentication required", code="missing_token")
    claims = decode_access_token(settings, token)
    user = await users.get(claims.get("sub", ""))
    if user is None:
        raise AuthenticationError("user not found", code="user_not_found")
    if not getattr(user, "is_active", True):
        raise AuthenticationError("account is disabled", code="account_disabled")
    request.state.user = user
    request.state.role = getattr(user, "role", "user")
    return user


async def get_optional_user(
    request: Request,
    settings: Settings = Depends(get_settings),
    users: UserRepository = Depends(get_user_repo),
) -> Any | None:
    token = _extract_bearer(request)
    if token is None:
        token = request.cookies.get(settings.access_token_cookie_name)
    if not token:
        return None
    try:
        claims = decode_access_token(settings, token)
        user = await users.get(claims.get("sub", ""))
        if user is None or not getattr(user, "is_active", True):
            return None
        request.state.user = user
        request.state.role = getattr(user, "role", "user")
        return user
    except AuthenticationError:
        return None


def require_admin(user: Any = Depends(get_current_user)) -> Any:
    if getattr(user, "role", "user") != "admin":
        raise AuthorizationError("admin privileges required")
    return user
