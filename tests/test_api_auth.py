from __future__ import annotations

from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.api import dependencies
from app.config import Settings
from app.generation.models import VerifiedResponse
from app.main import app


class FakePipeline:
    async def generate(self, query, **kwargs) -> VerifiedResponse:
        return VerifiedResponse(
            query=query,
            answer="The plaintiff must prove negligence by the defendant [1].",
            model="mock",
            elapsed_ms=12,
            quality_score=0.9,
            confidence=None,
        )

    async def stream(self, query, **kwargs):
        yield '{"type": "start", "query": "%s"}\n' % query
        yield '{"type": "token", "text": "mock"}\n'
        yield (
            '{"type": "result", "result": {"answer": "The plaintiff must prove '
            'negligence [1].", "sources": [], "citations": [], '
            '"confidence": {"overall": 0.9}, "elapsed_ms": 12}}\n'
        )


@pytest.fixture
def api():
    app.dependency_overrides.clear()
    app.dependency_overrides[dependencies.get_generation] = lambda: FakePipeline()
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()


def register(client: TestClient, email: str = "user@example.com") -> dict[str, Any]:
    response = client.post(
        "/api/auth/register",
        json={
            "email": email,
            "password": "password123",
            "full_name": "Test User",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def auth_headers(tokens: dict[str, Any]) -> dict[str, str]:
    return {"Authorization": f"Bearer {tokens['access_token']}"}


def test_register_login_me(api):
    tokens = register(api)
    assert tokens["access_token"]
    assert tokens["refresh_token"]
    assert tokens["user"]["email"] == "user@example.com"

    me = api.get("/api/auth/me", headers=auth_headers(tokens))
    assert me.status_code == 200
    assert me.json()["email"] == "user@example.com"

    login = api.post(
        "/api/auth/login",
        json={"email": "user@example.com", "password": "password123"},
    )
    assert login.status_code == 200
    assert login.json()["user"]["email"] == "user@example.com"


def test_register_duplicate_email(api):
    register(api)
    response = api.post(
        "/api/auth/register",
        json={"email": "user@example.com", "password": "password123", "full_name": "X"},
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "user_already_exists"


def test_login_wrong_password(api):
    register(api)
    response = api.post(
        "/api/auth/login",
        json={"email": "user@example.com", "password": "wrongpass1"},
    )
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "invalid_credentials"


def test_me_requires_auth(api):
    assert api.get("/api/auth/me").status_code == 401
    assert api.get("/api/auth/me", headers={"Authorization": "Bearer bad.token.x"}).status_code == 401


def test_refresh_rotates_token(api):
    tokens = register(api)
    refreshed = api.post("/api/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert refreshed.status_code == 200
    new = refreshed.json()
    assert new["access_token"]
    assert new["refresh_token"] != tokens["refresh_token"]

    # Reused old refresh token must be rejected and revoke the session.
    reused = api.post("/api/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert reused.status_code == 401

    # The rotated token is now also invalid because the family was revoked.
    revoked = api.post("/api/auth/refresh", json={"refresh_token": new["refresh_token"]})
    assert revoked.status_code == 401


def test_logout_revokes_session(api):
    tokens = register(api)
    out = api.post("/api/auth/logout", json={"refresh_token": tokens["refresh_token"]})
    assert out.status_code == 204
    assert api.post("/api/auth/refresh", json={"refresh_token": tokens["refresh_token"]}).status_code == 401


def test_logout_all(api):
    tokens = register(api)
    first = api.post("/api/auth/refresh", json={"refresh_token": tokens["refresh_token"]}).json()
    out = api.post("/api/auth/logout-all", headers=auth_headers(first))
    assert out.status_code == 204
    assert api.post("/api/auth/refresh", json={"refresh_token": tokens["refresh_token"]}).status_code == 401
    assert api.post("/api/auth/refresh", json={"refresh_token": first["refresh_token"]}).status_code == 401


def test_auth_rate_limit(api):
    for _ in range(10):
        api.post("/api/auth/login", json={"email": "a@b.com", "password": "password123"})
    response = api.post("/api/auth/login", json={"email": "a@b.com", "password": "password123"})
    assert response.status_code == 429
    assert response.json()["error"]["code"] == "rate_limit_exceeded"


def test_csrf_blocks_cookie_auth_without_token(api):
    register(api)
    api.get("/metrics")
    csrf = api.cookies.get("csrf_token")
    assert csrf

    blocked = api.post(
        "/api/conversations",
        json={"title": "no csrf header"},
    )
    assert blocked.status_code == 403
    assert blocked.json()["error"]["code"] == "csrf_error"

    allowed = api.post(
        "/api/conversations",
        headers={"X-CSRF-Token": csrf},
        json={"title": "with csrf header"},
    )
    assert allowed.status_code == 201


def test_update_profile(api):
    tokens = register(api)
    response = api.patch(
        "/api/auth/me",
        headers=auth_headers(tokens),
        json={"full_name": "Renamed", "preferences": {"theme": "dark"}},
    )
    assert response.status_code == 200
    assert response.json()["full_name"] == "Renamed"


def test_change_password(api):
    tokens = register(api)
    response = api.post(
        "/api/auth/change-password",
        headers=auth_headers(tokens),
        json={"current_password": "password123", "new_password": "newpassword456"},
    )
    assert response.status_code == 204
    login = api.post(
        "/api/auth/login",
        json={"email": "user@example.com", "password": "newpassword456"},
    )
    assert login.status_code == 200
