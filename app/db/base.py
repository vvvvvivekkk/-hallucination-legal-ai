from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, MetaData
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from ..config import Settings

NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)


def utcnow() -> datetime:
    from datetime import timezone

    return datetime.now(timezone.utc).replace(tzinfo=None)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), default=utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), default=utcnow, onupdate=utcnow, nullable=False
    )


class EngineState:
    """Lazily-initialized async engine shared process-wide."""

    def __init__(self) -> None:
        self._engine = None
        self._session_factory: sessionmaker | None = None
        self._url: str | None = None

    def configure(self, settings: Settings) -> None:
        if self._engine is not None:
            return
        if not settings.database_url:
            raise RuntimeError(
                "DATABASE_URL is not configured; cannot create database engine"
            )
        url = settings.database_url
        if url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql+asyncpg://", 1)
        elif url.startswith("postgresql://"):
            url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
        self._url = url
        self._engine = create_async_engine(
            url,
            echo=settings.db_echo,
            pool_size=settings.db_pool_size,
            max_overflow=settings.db_max_overflow,
            pool_pre_ping=True,
        )
        self._session_factory = sessionmaker(
            self._engine, class_=AsyncSession, expire_on_commit=False
        )

    @property
    def engine(self):
        if self._engine is None:
            raise RuntimeError("database engine not configured")
        return self._engine

    @property
    def session_factory(self) -> sessionmaker:
        if self._session_factory is None:
            raise RuntimeError("database engine not configured")
        return self._session_factory

    async def dispose(self) -> None:
        if self._engine is not None:
            await self._engine.dispose()
            self._engine = None
            self._session_factory = None


engine_state = EngineState()


def get_session_factory(settings: Settings) -> sessionmaker:
    engine_state.configure(settings)
    return engine_state.session_factory


async def init_db() -> None:
    """Create tables if the database engine is configured and they do not exist."""
    from . import models  # noqa: F401  (register tables with Base.metadata)

    settings = Settings()
    if not settings.database_url:
        return
    engine_state.configure(settings)
    async with engine_state.engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
