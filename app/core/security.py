from __future__ import annotations

import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any

import bcrypt
import jwt

from ..config import Settings
from .exceptions import AuthenticationError, ValidationError
from .logger import get_logger

logger = get_logger(__name__)


def hash_password(password: str, rounds: int = 12) -> str:
    if not password:
        raise ValidationError("password must not be empty")
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(rounds=rounds)).decode(
        "utf-8"
    )


def verify_password(password: str, password_hash: str) -> bool:
    if not password or not password_hash:
        return False
    try:
        return bcrypt.checkpw(
            password.encode("utf-8"), password_hash.encode("utf-8")
        )
    except (ValueError, TypeError):
        return False


def generate_token_identifier() -> str:
    """High-entropy opaque identifier used for refresh-token lookup."""
    return secrets.token_urlsafe(32)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def create_access_token(
    settings: Settings,
    user_id: str,
    role: str,
    token_id: str | None = None,
    extra: dict[str, Any] | None = None,
) -> str:
    issued = _now()
    expires = issued + timedelta(minutes=settings.jwt_access_token_minutes)
    claims: dict[str, Any] = {
        "sub": str(user_id),
        "role": role,
        "type": "access",
        "iat": issued,
        "exp": expires,
        "iss": settings.jwt_issuer,
        "aud": settings.jwt_audience,
        "jti": token_id or secrets.token_urlsafe(16),
    }
    if extra:
        claims.update(extra)
    return jwt.encode(
        claims, settings.jwt_secret, algorithm=settings.jwt_algorithm
    )


def decode_access_token(settings: Settings, token: str) -> dict[str, Any]:
    try:
        claims = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
            audience=settings.jwt_audience,
            issuer=settings.jwt_issuer,
        )
    except jwt.ExpiredSignatureError as exc:
        raise AuthenticationError("access token has expired", code="token_expired") from exc
    except jwt.InvalidTokenError as exc:
        raise AuthenticationError("invalid access token", code="invalid_token") from exc
    if claims.get("type") != "access":
        raise AuthenticationError("not an access token", code="invalid_token")
    return claims


def hash_refresh_token(token: str) -> str:
    """SHA-256 digest of a refresh token; the plaintext is never stored."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def constant_time_equals(left: str, right: str) -> bool:
    return hmac.compare_digest(left.encode("utf-8"), right.encode("utf-8"))
