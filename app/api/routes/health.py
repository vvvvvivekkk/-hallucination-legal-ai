from __future__ import annotations

import time

from fastapi import APIRouter, Depends

from ...config import Settings
from ...retrieval.qdrant import QdrantStore
from ..dependencies import get_settings, get_store
from ..schemas import HealthResponse

router = APIRouter(prefix="/api", tags=["health"])

_STARTED_AT = time.monotonic()


@router.get("/health", response_model=HealthResponse)
async def health(
    settings: Settings = Depends(get_settings),
    store: QdrantStore = Depends(get_store),
) -> HealthResponse:
    points: int | None = None
    qdrant_up = False
    try:
        qdrant_up = store.ping()
        if qdrant_up:
            info = store.collection_info(settings.qdrant_collection)
            points = int(info.get("points", 0))
    except Exception:
        qdrant_up = False

    return HealthResponse(
        status="ok" if qdrant_up else "degraded",
        service=settings.project_name,
        version=settings.version,
        collection=settings.qdrant_collection,
        points=points,
        qdrant="up" if qdrant_up else "down",
        uptime_seconds=round(time.monotonic() - _STARTED_AT, 3),
    )
