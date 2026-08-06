from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Request, Response

from ...config import Settings
from ...core.exceptions import ValidationError
from ...core.ratelimit import RateLimiter
from ...services.auth import AuthService, serialize_user
from ..dependencies import get_settings
from ..schemas import (
    LoginRequest,
    PasswordChangeRequest,
    ProfileUpdateRequest,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
    UserModel,
)
from ..security_deps import (
    get_client_ip,
    get_current_user,
    get_rate_limiter,
    get_session_repo,
    get_user_agent,
    get_user_repo,
)

router = APIRouter(prefix="/api/auth", tags=["auth"])


def _auth_service(
    settings: Settings = Depends(get_settings),
    users=Depends(get_user_repo),
    sessions=Depends(get_session_repo),
) -> AuthService:
    return AuthService(users, sessions, settings)


def _set_auth_cookies(response: Response, settings: Settings, tokens) -> None:
    response.set_cookie(
        settings.access_token_cookie_name,
        tokens.access_token,
        httponly=True,
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite,
        max_age=settings.jwt_access_token_minutes * 60,
        path="/",
    )
    response.set_cookie(
        settings.refresh_token_cookie_name,
        tokens.refresh_token,
        httponly=True,
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite,
        max_age=settings.jwt_refresh_token_days * 24 * 3600,
        path="/",
    )


def _clear_auth_cookies(response: Response, settings: Settings) -> None:
    for name in (settings.access_token_cookie_name, settings.refresh_token_cookie_name):
        response.delete_cookie(name, path="/")


@router.post("/register", response_model=TokenResponse, status_code=201)
async def register(
    request: Request,
    response: Response,
    body: RegisterRequest,
    auth: AuthService = Depends(_auth_service),
    limiter: RateLimiter = Depends(get_rate_limiter),
    settings: Settings = Depends(get_settings),
) -> TokenResponse:
    limiter.check(
        f"auth:register:{get_client_ip(request) or 'unknown'}",
        settings.auth_rate_limit_requests,
        settings.auth_rate_limit_window_seconds,
    )
    tokens = await auth.register(
        body.email,
        body.password,
        body.full_name,
        user_agent=get_user_agent(request),
        ip_address=get_client_ip(request),
    )
    _set_auth_cookies(response, settings, tokens)
    return TokenResponse(**tokens.to_dict())


@router.post("/login", response_model=TokenResponse)
async def login(
    request: Request,
    response: Response,
    body: LoginRequest,
    auth: AuthService = Depends(_auth_service),
    limiter: RateLimiter = Depends(get_rate_limiter),
    settings: Settings = Depends(get_settings),
) -> TokenResponse:
    limiter.check(
        f"auth:login:{get_client_ip(request) or 'unknown'}",
        settings.auth_rate_limit_requests,
        settings.auth_rate_limit_window_seconds,
    )
    tokens = await auth.login(
        body.email,
        body.password,
        user_agent=get_user_agent(request),
        ip_address=get_client_ip(request),
    )
    _set_auth_cookies(response, settings, tokens)
    return TokenResponse(**tokens.to_dict())


@router.post("/refresh", response_model=TokenResponse)
async def refresh(
    request: Request,
    response: Response,
    body: RefreshRequest,
    auth: AuthService = Depends(_auth_service),
    settings: Settings = Depends(get_settings),
) -> TokenResponse:
    token = body.refresh_token or request.cookies.get(settings.refresh_token_cookie_name)
    tokens = await auth.refresh(
        token,
        user_agent=get_user_agent(request),
        ip_address=get_client_ip(request),
    )
    _set_auth_cookies(response, settings, tokens)
    return TokenResponse(**tokens.to_dict())


@router.post("/logout", status_code=204)
async def logout(
    request: Request,
    response: Response,
    body: RefreshRequest,
    auth: AuthService = Depends(_auth_service),
    settings: Settings = Depends(get_settings),
) -> Response:
    token = body.refresh_token or request.cookies.get(settings.refresh_token_cookie_name)
    await auth.logout(token)
    _clear_auth_cookies(response, settings)
    response.status_code = 204
    return response


@router.post("/logout-all", status_code=204)
async def logout_all(
    response: Response,
    user: Any = Depends(get_current_user),
    auth: AuthService = Depends(_auth_service),
    settings: Settings = Depends(get_settings),
) -> Response:
    await auth.logout_all(user.id)
    _clear_auth_cookies(response, settings)
    response.status_code = 204
    return response


@router.get("/me", response_model=UserModel)
async def me(user: Any = Depends(get_current_user)) -> UserModel:
    return UserModel(**serialize_user(user))


@router.patch("/me", response_model=UserModel)
async def update_profile(
    body: ProfileUpdateRequest,
    user: Any = Depends(get_current_user),
    users=Depends(get_user_repo),
) -> UserModel:
    fields: dict[str, Any] = {}
    if body.full_name is not None:
        fields["full_name"] = body.full_name.strip()
    if body.avatar_url is not None:
        fields["avatar_url"] = body.avatar_url.strip() or None
    if body.preferences is not None:
        fields["preferences"] = body.preferences
    if not fields:
        raise ValidationError("no fields to update")
    updated = await users.update(user, **fields)
    return UserModel(**serialize_user(updated))


@router.post("/change-password", status_code=204)
async def change_password(
    body: PasswordChangeRequest,
    user: Any = Depends(get_current_user),
    users=Depends(get_user_repo),
    settings: Settings = Depends(get_settings),
    auth: AuthService = Depends(_auth_service),
) -> Response:
    from ...core.security import hash_password, verify_password

    if not verify_password(body.current_password, user.password_hash):
        raise ValidationError("current password is incorrect")
    await users.update(
        user, password_hash=hash_password(body.new_password, settings.bcrypt_rounds)
    )
    await auth.logout_all(user.id)
    return Response(status_code=204)
