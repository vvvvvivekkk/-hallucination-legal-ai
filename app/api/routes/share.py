from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends

from ...core.exceptions import NotFoundError
from ...services.conversations import ConversationService
from ..schemas import ConversationDetail, MessageModel
from ..security_deps import get_conversation_repo, get_message_repo, get_share_repo

router = APIRouter(prefix="/api/share", tags=["share"])


def _service(
    conversations=Depends(get_conversation_repo),
    messages=Depends(get_message_repo),
    shares=Depends(get_share_repo),
) -> ConversationService:
    return ConversationService(conversations, messages, shares)


@router.get("/{slug}", response_model=ConversationDetail)
async def get_public_share(
    slug: str,
    service: ConversationService = Depends(_service),
) -> ConversationDetail:
    data = await service.public_share(slug)
    if data is None:
        raise NotFoundError("share link not found or expired")
    return ConversationDetail(
        id=data["conversation_id"],
        title=data["title"],
        is_pinned=False,
        created_at=data["created_at"],
        updated_at=data["updated_at"],
        last_message_at=data.get("last_message_at"),
        messages=[MessageModel(**message) for message in data["messages"]],
    )
