from __future__ import annotations

import re
import secrets
from dataclasses import dataclass
from datetime import timedelta
from typing import Any

from ..config import Settings
from ..core.exceptions import (
    AuthenticationError,
    UserAlreadyExistsError,
    ValidationError,
)
from ..core.security import (
    create_access_token,
    generate_token_identifier,
    hash_password,
    hash_refresh_token,
    verify_password,
)
from ..repositories.base import SessionRepository, UserRepository
from ..db.models import utcnow

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
VALID_ROLES = {"user", "admin"}


@dataclass
class AuthTokens:
    access_token: str
    refresh_token: str
    user: dict[str, Any]
    token_type: str = "bearer"
    expires_in: int = 900

    def to_dict(self) -> dict[str, Any]:
        return {
            "access_token": self.access_token,
            "refresh_token": self.refresh_token,
            "token_type": self.token_type,
            "expires_in": self.expires_in,
            "user": self.user,
        }


def serialize_user(user: Any) -> dict[str, Any]:
    return {
        "id": user.id,
        "email": user.email,
        "full_name": user.full_name,
        "role": user.role,
        "is_active": getattr(user, "is_active", True),
        "avatar_url": getattr(user, "avatar_url", None),
        "preferences": getattr(user, "preferences", {}),
        "created_at": _iso(user.created_at),
        "last_login_at": _iso(getattr(user, "last_login_at", None)),
    }


def _iso(value) -> str | None:
    if value is None:
        return None
    return value.isoformat() if hasattr(value, "isoformat") else str(value)


class AuthService:
    def __init__(
        self,
        users: UserRepository,
        sessions: SessionRepository,
        settings: Settings,
    ) -> None:
        self._users = users
        self._sessions = sessions
        self._settings = settings

    async def register(
        self,
        email: str,
        password: str,
        full_name: str,
        *,
        role: str = "user",
        user_agent: str | None = None,
        ip_address: str | None = None,
    ) -> AuthTokens:
        email = (email or "").strip().lower()
        full_name = (full_name or "").strip()
        self._validate_email(email)
        self._validate_password(password)
        if not full_name:
            raise ValidationError("full_name must not be empty")
        role = (role or "user").lower()
        if role not in VALID_ROLES:
            raise ValidationError("invalid role")
        if await self._users.get_by_email(email):
            raise UserAlreadyExistsError(f"an account already exists for {email}")
        user = await self._users.create(
            email=email,
            full_name=full_name[:120],
            password_hash=hash_password(password, self._settings.bcrypt_rounds),
            role=role,
        )
        return await self._issue_tokens(user, user_agent, ip_address)

    async def login(
        self,
        email: str,
        password: str,
        *,
        user_agent: str | None = None,
        ip_address: str | None = None,
    ) -> AuthTokens:
        email = (email or "").strip().lower()
        user = await self._users.get_by_email(email)
        if user is None or not verify_password(password or "", user.password_hash):
            raise AuthenticationError("invalid email or password", code="invalid_credentials")
        if not getattr(user, "is_active", True):
            raise AuthenticationError("account is disabled", code="account_disabled")
        await self._users.touch_login(user)
        return await self._issue_tokens(user, user_agent, ip_address)

    async def refresh(
        self,
        refresh_token: str,
        *,
        user_agent: str | None = None,
        ip_address: str | None = None,
    ) -> AuthTokens:
        if not refresh_token:
            raise AuthenticationError("refresh token is required", code="invalid_refresh_token")
        token_hash = hash_refresh_token(refresh_token)
        session = await self._sessions.get_by_hash(token_hash)
        if session is None:
            raise AuthenticationError("invalid refresh token", code="invalid_refresh_token")
        if session.revoked_at is not None:
            # Reuse of a rotated token indicates possible theft; revoke the family.
            await self._sessions.revoke_all_for_user(session.user_id)
            raise AuthenticationError(
                "refresh token reuse detected; all sessions revoked",
                code="refresh_token_reuse",
            )
        if session.expires_at and session.expires_at < utcnow():
            await self._sessions.revoke(session)
            raise AuthenticationError("refresh token has expired", code="token_expired")
        user = await self._users.get(session.user_id)
        if user is None:
            raise AuthenticationError("user not found", code="invalid_refresh_token")
        if not getattr(user, "is_active", True):
            raise AuthenticationError("account is disabled", code="account_disabled")
        return await self._issue_tokens(
            user, user_agent, ip_address, previous_session=session
        )

    async def logout(self, refresh_token: str) -> None:
        if not refresh_token:
            raise ValidationError("refresh token is required")
        session = await self._sessions.get_by_hash(hash_refresh_token(refresh_token))
        if session is not None and session.revoked_at is None:
            await self._sessions.revoke(session)

    async def logout_all(self, user_id: str) -> None:
        await self._sessions.revoke_all_for_user(user_id)

    async def _issue_tokens(
        self,
        user: Any,
        user_agent: str | None,
        ip_address: str | None,
        *,
        previous_session: Any | None = None,
    ) -> AuthTokens:
        raw_refresh = f"{generate_token_identifier()}.{secrets.token_urlsafe(32)}"
        token_hash = hash_refresh_token(raw_refresh)
        expires_at = utcnow() + timedelta(days=self._settings.jwt_refresh_token_days)
        session = await self._sessions.create(
            user_id=user.id,
            token_hash=token_hash,
            user_agent=user_agent,
            ip_address=ip_address,
            expires_at=expires_at,
        )
        if previous_session is not None:
            await self._sessions.mark_replaced(previous_session, token_hash)
        access = create_access_token(
            self._settings, user.id, user.role, token_id=session.id
        )
        return AuthTokens(
            access_token=access,
            refresh_token=raw_refresh,
            expires_in=self._settings.jwt_access_token_minutes * 60,
            user=serialize_user(user),
        )

    def _validate_email(self, email: str) -> None:
        if not _EMAIL_RE.match(email):
            raise ValidationError("invalid email address")

    def _validate_password(self, password: str) -> None:
        if not password or len(password) < self._settings.password_min_length:
            raise ValidationError(
                f"password must be at least {self._settings.password_min_length} characters"
            )
