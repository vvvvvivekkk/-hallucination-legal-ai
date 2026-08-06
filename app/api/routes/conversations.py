from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter, Depends, Query
from fastapi.responses import PlainTextResponse

from ...core.exceptions import NotFoundError
from ...services.conversations import ConversationService
from ..dependencies import get_settings
from ..schemas import (
    ConversationCreateRequest,
    ConversationDetail,
    ConversationListResponse,
    ConversationModel,
    ConversationUpdateRequest,
    ExportResponse,
    ShareRequest,
    ShareResponse,
)
from ..security_deps import (
    get_conversation_repo,
    get_current_user,
    get_message_repo,
    get_share_repo,
)

router = APIRouter(prefix="/api/conversations", tags=["conversations"])


def _service(
    conversations=Depends(get_conversation_repo),
    messages=Depends(get_message_repo),
    shares=Depends(get_share_repo),
) -> ConversationService:
    return ConversationService(conversations, messages, shares)


@router.get("", response_model=ConversationListResponse)
async def list_conversations(
    user: Any = Depends(get_current_user),
    service: ConversationService = Depends(_service),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    search: str | None = Query(default=None, max_length=200),
    pinned: bool = Query(default=False),
) -> ConversationListResponse:
    data = await service.list(
        user.id, offset=offset, limit=limit, search=search, pinned_only=pinned
    )
    return ConversationListResponse(**data)


@router.post("", response_model=ConversationModel, status_code=201)
async def create_conversation(
    body: ConversationCreateRequest,
    user: Any = Depends(get_current_user),
    service: ConversationService = Depends(_service),
) -> ConversationModel:
    record = await service.create(
        user.id, title=body.title, model=body.model, collection=body.collection
    )
    return ConversationModel(**record)


@router.get("/{conversation_id}", response_model=ConversationDetail)
async def get_conversation(
    conversation_id: str,
    user: Any = Depends(get_current_user),
    service: ConversationService = Depends(_service),
) -> ConversationDetail:
    data = await service.get(conversation_id, user.id)
    return ConversationDetail(**data)


@router.patch("/{conversation_id}", response_model=ConversationModel)
async def update_conversation(
    conversation_id: str,
    body: ConversationUpdateRequest,
    user: Any = Depends(get_current_user),
    service: ConversationService = Depends(_service),
) -> ConversationModel:
    record = await service.update(
        conversation_id, user.id, title=body.title, is_pinned=body.is_pinned
    )
    return ConversationModel(**record)


@router.delete("/{conversation_id}", status_code=204)
async def delete_conversation(
    conversation_id: str,
    user: Any = Depends(get_current_user),
    service: ConversationService = Depends(_service),
) -> None:
    await service.delete(conversation_id, user.id)


@router.post("/{conversation_id}/share", response_model=ShareResponse)
async def share_conversation(
    conversation_id: str,
    body: ShareRequest,
    user: Any = Depends(get_current_user),
    service: ConversationService = Depends(_service),
    settings=Depends(get_settings),
) -> ShareResponse:
    data = await service.share(
        conversation_id, user.id, expires_in_days=body.expires_in_days
    )
    public_base = getattr(settings, "public_base_url", None) or "http://localhost:8000"
    return ShareResponse(
        url=f"{public_base}/share/{data['slug']}",
        slug=data["slug"],
        expires_at=data["expires_at"],
    )


@router.delete("/{conversation_id}/share", status_code=204)
async def revoke_share(
    conversation_id: str,
    user: Any = Depends(get_current_user),
    service: ConversationService = Depends(_service),
) -> None:
    await service.revoke_share(conversation_id, user.id)


@router.get("/{conversation_id}/export", response_class=PlainTextResponse)
async def export_conversation(
    conversation_id: str,
    user: Any = Depends(get_current_user),
    service: ConversationService = Depends(_service),
) -> PlainTextResponse:
    data = await service.get(conversation_id, user.id)
    lines = [f"# {data['title']}", ""]
    for message in data["messages"]:
        role = "User" if message["role"] == "user" else "Assistant"
        lines.append(f"## {role}")
        lines.append(message["content"])
        lines.append("")
    return PlainTextResponse("\n".join(lines), media_type="text/markdown")


class PublicShare:
    def __init__(self) -> None:
        self.last: dict[str, Any] | None = None
