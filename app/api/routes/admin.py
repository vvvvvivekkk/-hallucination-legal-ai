from __future__ import annotations

import time
from typing import Any

from fastapi import APIRouter, Depends
from fastapi.responses import Response

from ...core.metrics import REGISTRY, metrics_response
from ...services.auth import AuthService, serialize_user
from ...services.conversations import ConversationService
from ..schemas import AdminUserUpdate, SystemStats, UserModel
from ..security_deps import (
    get_conversation_repo,
    get_current_user,
    get_message_repo,
    get_share_repo,
    get_user_repo,
    require_admin,
)
from .auth import _auth_service

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.get("/users", response_model=list[UserModel])
async def list_users(
    admin: Any = Depends(require_admin),
    users=Depends(get_user_repo),
) -> list[UserModel]:
    records = await users.list_all()
    return [UserModel(**serialize_user(record)) for record in records]


@router.patch("/users/{user_id}", response_model=UserModel)
async def update_user(
    user_id: str,
    body: AdminUserUpdate,
    admin: Any = Depends(require_admin),
    users=Depends(get_user_repo),
) -> UserModel:
    record = await users.get_by_id(user_id)
    if record is None:
        from ...core.exceptions import NotFoundError

        raise NotFoundError("user not found")
    fields: dict[str, Any] = {}
    if body.role is not None:
        fields["role"] = body.role
    if body.is_active is not None:
        fields["is_active"] = body.is_active
    if fields:
        record = await users.update(record, **fields)
    return UserModel(**serialize_user(record))


@router.get("/stats", response_model=SystemStats)
async def system_stats(
    admin: Any = Depends(require_admin),
    users=Depends(get_user_repo),
    conversations=Depends(get_conversation_repo),
    messages=Depends(get_message_repo),
) -> SystemStats:
    return SystemStats(
        users=await users.count(),
        conversations=await conversations.count(),
        messages=await messages.count(),
        qdrant_points=0,
        uptime_seconds=time.monotonic() - _STARTED_AT,
    )


_STARTED_AT = time.monotonic()


@router.get("/metrics")
async def metrics(
    admin: Any = Depends(require_admin),
) -> Response:
    return metrics_response(REGISTRY)
