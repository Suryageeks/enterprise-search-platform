from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import settings


read_only_engine = create_async_engine(
    settings.agent_read_database_url,
    pool_pre_ping=True,
)

ReadOnlySessionLocal = async_sessionmaker(
    bind=read_only_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

async def get_read_only_session() -> AsyncIterator[AsyncSession]:
    async with ReadOnlySessionLocal() as session:
        yield session


async def close_read_only_engine() -> None:
    await read_only_engine.dispose()
