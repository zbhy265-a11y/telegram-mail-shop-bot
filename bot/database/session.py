import logging
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from bot.config import config
from bot.database.base import Base

logger = logging.getLogger(__name__)

_engine = None
_session_maker = None

def init_engine() -> None:
    global _engine, _session_maker
    if _engine is not None:
        return

    url = config.database_url
    if not url:
        raise ValueError(
            "DATABASE_URL is not set.\n\n"
            "Railway fix:\n"
            "1. Add PostgreSQL database to your project\n"
            "2. worker → Variables → + New Variable → Add Reference\n"
            "3. Select PostgreSQL → choose DATABASE_URL → Add"
        )

    logger.warning(f"DATABASE URL = {url}")

    _engine = create_async_engine(
        url,
        echo=False,
        pool_size=10,
        max_overflow=20,
        pool_pre_ping=True,
        pool_recycle=3600,
    )

    _session_maker = async_sessionmaker(
        _engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    logger.info("Database engine initialized")

def async_session():
    if _session_maker is None:
        init_engine()
    return _session_maker()

async def init_db() -> None:
    init_engine()
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    logger.info("Database tables initialized")

async def close_db() -> None:
    if _engine is not None:
        await _engine.dispose()
        logger.info("Database connection closed")

@asynccontextmanager
async def get_session():
    async with async_session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
