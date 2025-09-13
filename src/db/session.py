from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase
from src.core.config import get_settings


settings = get_settings()


class Base(DeclarativeBase):
    pass


engine = create_async_engine(settings.sqlalchemy_dsn(), pool_pre_ping=True, pool_recycle=3600)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


async def get_session() -> AsyncSession:
    async with SessionLocal() as session:
        yield session

