from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from . import __version__
from .api.dependencies import get_settings
from .api.errors import register_exception_handlers
from .api.routes import (
    admin as admin_routes,
)
from .api.routes import (
    auth as auth_routes,
)
from .api.routes import (
    chat as chat_routes,
)
from .api.routes import (
    conversations as conversations_routes,
)
from .api.routes import generation as generation_routes
from .api.routes import health as health_routes
from .api.routes import ingest as ingest_routes
from .api.routes import search as search_routes
from .api.routes import share as share_routes
from .core.logger import get_logger, setup_logging
from .core.middleware import CSRFMiddleware, RequestContextMiddleware
from .db.base import init_db


def create_app() -> FastAPI:
    settings = get_settings()
    setup_logging(settings.log_level, settings.log_json)
    logger = get_logger(__name__)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        logger.info("Starting %s v%s", settings.project_name, settings.version)
        if settings.database_url:
            await init_db()
        from .services.watcher import start_watcher

        watcher = None
        if settings.auto_ingest_enabled:
            watcher = await start_watcher()
        yield
        if watcher is not None:
            await watcher.stop()
        logger.info("Shutting down %s", settings.project_name)

    application = FastAPI(
        title=settings.project_name,
        version=settings.version,
        description="Reducing hallucinations in Legal AI using Retrieval-Augmented Generation",
        lifespan=lifespan,
    )
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    if settings.enable_prometheus:
        application.add_middleware(
            RequestContextMiddleware, settings=settings
        )
        application.add_middleware(CSRFMiddleware, settings=settings)
    application.include_router(ingest_routes.router)
    application.include_router(search_routes.router)
    application.include_router(generation_routes.router)
    application.include_router(health_routes.router)
    application.include_router(auth_routes.router)
    application.include_router(conversations_routes.router)
    application.include_router(chat_routes.router)
    application.include_router(share_routes.router)
    application.include_router(admin_routes.router)

    if settings.enable_prometheus:
        from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

        from .core.metrics import REGISTRY

        @application.get("/metrics", include_in_schema=False)
        async def metrics_endpoint():
            from fastapi.responses import Response as FastAPIResponse

            return FastAPIResponse(
                content=generate_latest(REGISTRY), media_type=CONTENT_TYPE_LATEST
            )

    register_exception_handlers(application)
    return application


app = create_app()
