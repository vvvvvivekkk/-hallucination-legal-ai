from __future__ import annotations

import secrets
import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from ..config import Settings
from .logger import get_logger
from .metrics import (
    HTTP_REQUESTS_INFLIGHT,
    HTTP_REQUESTS_TOTAL,
    HTTP_REQUEST_DURATION,
)

logger = get_logger(__name__)

SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
    "X-XSS-Protection": "0",
}

_CSP = (
    "default-src 'self'; "
    "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
    "style-src 'self' 'unsafe-inline'; "
    "img-src 'self' data: blob:; "
    "font-src 'self' data:; "
    "connect-src 'self' ws: wss:; "
    "worker-src 'self' blob:; "
    "frame-ancestors 'none'; "
    "base-uri 'self'; "
    "form-action 'self'"
)


class RequestContextMiddleware(BaseHTTPMiddleware):
    """Adds a request ID, security headers, and response timing."""

    def __init__(self, app, settings: Settings) -> None:
        super().__init__(app)
        self._settings = settings

    async def dispatch(self, request: Request, call_next) -> Response:
        request_id = request.headers.get("x-request-id") or str(uuid.uuid4())
        request.state.request_id = request_id
        start = time.monotonic()
        method = request.method
        path = request.url.path
        HTTP_REQUESTS_INFLIGHT.labels(method=method).inc()
        try:
            response = await call_next(request)
        except Exception:
            HTTP_REQUESTS_TOTAL.labels(
                method=method, path=path, status="500"
            ).inc()
            raise
        finally:
            HTTP_REQUESTS_INFLIGHT.labels(method=method).dec()
        duration = time.monotonic() - start
        HTTP_REQUESTS_TOTAL.labels(
            method=method, path=path, status=str(response.status_code)
        ).inc()
        HTTP_REQUEST_DURATION.labels(method=method, path=path).observe(duration)
        response.headers["X-Request-ID"] = request_id
        for header, value in SECURITY_HEADERS.items():
            response.headers[header] = value
        if not self._settings.environment.startswith("production"):
            response.headers["Content-Security-Policy"] = _CSP
        return response


class CSRFMiddleware(BaseHTTPMiddleware):
    """Double-submit CSRF protection for cookie-based auth flows.

    Only enforced on state-changing requests to cookie-auth-sensitive
    endpoints. Public API endpoints and bearer-authenticated requests
    are exempt.
    """

    DEFAULT_PROTECTED_PREFIXES = (
        "/api/conversations",
        "/api/admin",
        "/api/auth/me",
        "/api/auth/change-password",
        "/api/auth/logout-all",
    )
    DEFAULT_EXEMPT = {"/api/auth/register", "/api/auth/login", "/api/auth/refresh", "/api/auth/logout"}

    def __init__(
        self,
        app,
        settings: Settings,
        exempt_paths: set[str] | None = None,
        protected_prefixes: tuple[str, ...] | None = None,
    ) -> None:
        super().__init__(app)
        self._settings = settings
        self._header = settings.csrf_header_name
        self._cookie = "csrf_token"
        self._exempt = exempt_paths or self.DEFAULT_EXEMPT
        self._protected = protected_prefixes or self.DEFAULT_PROTECTED_PREFIXES

    async def dispatch(self, request: Request, call_next) -> Response:
        if request.method in {"GET", "HEAD", "OPTIONS", "TRACE"}:
            return await self._attach_token(request, call_next)
        path = request.url.path
        if path in self._exempt or path.startswith("/metrics"):
            return await call_next(request)
        if not path.startswith(self._protected):
            return await call_next(request)
        if request.headers.get("authorization"):
            return await call_next(request)
        cookie_token = request.cookies.get(self._cookie)
        header_token = request.headers.get(self._header)
        if cookie_token and header_token and secrets.compare_digest(cookie_token, header_token):
            return await call_next(request)
        return JSONResponse(
            status_code=403,
            content={
                "error": {
                    "code": "csrf_error",
                    "message": "CSRF token missing or invalid",
                }
            },
        )

    async def _attach_token(self, request: Request, call_next) -> Response:
        if self._cookie in request.cookies:
            return await call_next(request)
        response = await call_next(request)
        token = secrets.token_urlsafe(32)
        response.set_cookie(
            self._cookie,
            token,
            httponly=False,
            secure=self._settings.cookie_secure,
            samesite=self._settings.cookie_samesite,
            max_age=60 * 60 * 12,
        )
        return response
