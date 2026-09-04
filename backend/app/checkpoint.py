from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool

from app.config import Settings


def checkpoint_pool_options(settings: Settings) -> dict:
    """为云数据库 checkpoint 连接启用借出检查和定期回收。"""
    return {
        "min_size": 1,
        "max_size": 4,
        "timeout": settings.database_pool_timeout_seconds,
        "max_idle": min(60, settings.database_pool_recycle_seconds),
        "max_lifetime": settings.database_pool_recycle_seconds,
        "reconnect_timeout": settings.database_connect_timeout_seconds,
        "open": False,
        # 每次借出前执行轻量检查，淘汰被 Neon 回收的断开连接。
        "check": AsyncConnectionPool.check_connection,
        "kwargs": {
            "autocommit": True,
            "prepare_threshold": 0,
            "row_factory": dict_row,
        },
    }


def create_checkpoint_pool(settings: Settings) -> AsyncConnectionPool:
    """创建供 LangGraph checkpointer 使用的可自动重连连接池。"""
    return AsyncConnectionPool(
        conninfo=settings.checkpoint_database_url,
        **checkpoint_pool_options(settings),
    )
