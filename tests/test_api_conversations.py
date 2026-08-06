from __future__ import annotations

from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.api import dependencies
from app.generation.models import VerifiedResponse
from app.main import app


class FakePipeline:
    async def generate(self, query, **kwargs) -> VerifiedResponse:
        return VerifiedResponse(
            query=query,
            answer=f"Mock answer for: {query} [1].",
            model="mock",
            elapsed_ms=5,
            quality_score=0.8,
        )


@pytest.fixture
def api():
    app.dependency_overrides.clear()
    app.dependency_overrides[dependencies.get_generation] = lambda: FakePipeline()
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()


def register(client: TestClient, email: str = "conv@example.com") -> dict[str, str]:
    response = client.post(
        "/api/auth/register",
        json={"email": email, "password": "password123", "full_name": "Converser"},
    )
    assert response.status_code == 201, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_conversation_crud(api):
    headers = register(api)

    created = api.post("/api/conversations", headers=headers, json={"title": "Case notes"})
    assert created.status_code == 201
    conv = created.json()
    assert conv["title"] == "Case notes"
    conv_id = conv["id"]

    listing = api.get("/api/conversations", headers=headers)
    assert listing.status_code == 200
    assert listing.json()["total"] == 1
    assert listing.json()["items"][0]["id"] == conv_id

    updated = api.patch(f"/api/conversations/{conv_id}", headers=headers, json={"title": "Renamed", "is_pinned": True})
    assert updated.status_code == 200
    assert updated.json()["title"] == "Renamed"
    assert updated.json()["is_pinned"] is True

    pinned = api.get("/api/conversations", headers=headers, params={"pinned": True})
    assert pinned.json()["total"] == 1

    search = api.get("/api/conversations", headers=headers, params={"search": "Rena"})
    assert search.json()["total"] == 1

    other = register(api, email="other@example.com")
    forbidden = api.get(f"/api/conversations/{conv_id}", headers=other)
    assert forbidden.status_code == 404

    assert api.delete(f"/api/conversations/{conv_id}", headers=headers).status_code == 204
    assert api.get("/api/conversations", headers=headers).json()["total"] == 0


def test_chat_creates_and_persists_exchange(api):
    headers = register(api)
    response = api.post(
        "/api/conversations/chat",
        headers=headers,
        json={"message": "What is negligence?"},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["role"] == "assistant"
    assert body["conversation_id"]

    detail = api.get(f"/api/conversations/{body['conversation_id']}", headers=headers)
    assert detail.status_code == 200
    roles = [m["role"] for m in detail.json()["messages"]]
    assert roles == ["user", "assistant"]


def test_chat_requires_auth(api):
    assert api.post("/api/conversations/chat", json={"message": "hi"}).status_code in (401, 403)


def test_chat_empty_message_rejected(api):
    headers = register(api)
    response = api.post("/api/conversations/chat", headers=headers, json={"message": "   "})
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "validation_error"


def test_share_and_public_view(api):
    headers = register(api)
    created = api.post("/api/conversations", headers=headers, json={"title": "Share me"}).json()
    chat = api.post(
        "/api/conversations/chat",
        headers=headers,
        json={"message": "hello", "conversation_id": created["id"]},
    ).json()

    shared = api.post(f"/api/conversations/{created['id']}/share", headers=headers, json={"expires_in_days": 7})
    assert shared.status_code == 200
    slug = shared.json()["slug"]
    assert shared.json()["url"].endswith(f"/share/{slug}")

    public = api.get(f"/api/share/{slug}")
    assert public.status_code == 200
    assert public.json()["title"] == "Share me"
    assert len(public.json()["messages"]) == 2

    revoke = api.delete(f"/api/conversations/{created['id']}/share", headers=headers)
    assert revoke.status_code == 204
    assert api.get(f"/api/share/{slug}").status_code == 404


def test_export_markdown(api):
    headers = register(api)
    created = api.post("/api/conversations", headers=headers, json={"title": "Export"}).json()
    api.post(
        "/api/conversations/chat",
        headers=headers,
        json={"message": "hello", "conversation_id": created["id"]},
    )
    exported = api.get(f"/api/conversations/{created['id']}/export", headers=headers)
    assert exported.status_code == 200
    assert "text/markdown" in exported.headers["content-type"]
    assert "# Export" in exported.text
    assert "## Assistant" in exported.text


def test_admin_requires_admin_role(api):
    user_headers = register(api)
    response = api.get("/api/admin/users", headers=user_headers)
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "authorization_error"


def test_admin_users_and_stats(api):
    user_headers = register(api, email="admin@example.com")
    admin_user = api.get("/api/auth/me", headers=user_headers).json()
    from app.repositories.memory import MemoryStore
    from app.api.security_deps import get_memory_store

    store: MemoryStore = get_memory_store()
    user = store.users.get(admin_user["id"])
    user.role = "admin"

    users = api.get("/api/admin/users", headers=user_headers)
    assert users.status_code == 200
    assert any(u["email"] == "admin@example.com" for u in users.json())

    stats = api.get("/api/admin/stats", headers=user_headers)
    assert stats.status_code == 200
    assert stats.json()["users"] >= 1
    assert stats.json()["uptime_seconds"] >= 0


def test_metrics_endpoint(api):
    response = api.get("/metrics")
    assert response.status_code == 200
    assert "http_requests_total" in response.text
