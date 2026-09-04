from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import Settings, get_settings


class Base(DeclarativeBase):
    pass


settings = get_settings()


def database_engine_options(current_settings: Settings) -> dict:
    """限制连接等待时间，并定期回收云数据库可能已经失效的空闲连接。"""
    return {
        "pool_pre_ping": True,
        "pool_recycle": current_settings.database_pool_recycle_seconds,
        "pool_timeout": current_settings.database_pool_timeout_seconds,
        "connect_args": {
            "timeout": current_settings.database_connect_timeout_seconds,
        },
    }


engine = create_async_engine(settings.async_database_url, **database_engine_options(settings))
SessionLocal = async_sessionmaker(engine, expire_on_commit=False)


async def get_session() -> AsyncIterator[AsyncSession]:
    """为每个 FastAPI 请求提供独立 AsyncSession，并在结束后自动关闭。"""
    async with SessionLocal() as session:
        yield session
