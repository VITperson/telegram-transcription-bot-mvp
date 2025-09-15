from __future__ import annotations

import os
import asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase
from src.core.config import get_settings


settings = get_settings()


class Base(DeclarativeBase):
    pass


_engine = None
_session_maker = None
_pid = None


def _ensure_sessionmaker():
    """Ensure AsyncEngine/sessionmaker are initialized per worker process.

    We maintain a persistent event loop per Celery worker process, so binding to PID
    is sufficient and avoids cross-loop issues and MissingGreenlet during disposal.
    """
    global _engine, _session_maker, _pid
    pid = os.getpid()
    if _engine is None or _pid != pid:
        _engine = create_async_engine(settings.sqlalchemy_dsn(), pool_pre_ping=True, pool_recycle=3600)
        _session_maker = async_sessionmaker(_engine, expire_on_commit=False, class_=AsyncSession)
        _pid = pid


class _SessionLocalFactory:
    def __call__(self, *args, **kwargs):
        _ensure_sessionmaker()
        return _session_maker(*args, **kwargs)  # type: ignore[misc]


SessionLocal = _SessionLocalFactory()


async def get_session() -> AsyncSession:
    async with SessionLocal() as session:  # type: ignore[misc]
        yield session
