from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from . import __version__
from .api.dependencies import get_settings
from .api.errors import register_exception_handlers
from .api.routes import health as health_routes
from .api.routes import ingest as ingest_routes
from .api.routes import search as search_routes
from .core.logger import get_logger, setup_logging


def create_app() -> FastAPI:
    settings = get_settings()
    setup_logging(settings.log_level, settings.log_json)
    logger = get_logger(__name__)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        logger.info("Starting %s v%s", settings.project_name, settings.version)
        yield
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
    application.include_router(ingest_routes.router)
    application.include_router(search_routes.router)
    application.include_router(health_routes.router)
    register_exception_handlers(application)
    return application


app = create_app()
