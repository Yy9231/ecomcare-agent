from app.config import Settings
from app.database import database_engine_options


def test_neon_url_is_normalized_for_asyncpg() -> None:
    settings = Settings(
        _env_file=None,
        database_url=(
            "postgresql://demo:secret@example.neon.tech/neondb"
            "?sslmode=require&channel_binding=require"
        ),
    )

    assert settings.async_database_url == (
        "postgresql+asyncpg://demo:secret@example.neon.tech/neondb?ssl=require"
    )


def test_asyncpg_url_is_left_usable() -> None:
    settings = Settings(
        _env_file=None,
        database_url="postgresql+asyncpg://demo:secret@localhost:5432/ecomcare",
    )

    assert settings.async_database_url == settings.database_url


def test_database_engine_options_bound_neon_wait_times() -> None:
    settings = Settings(
        _env_file=None,
        database_connect_timeout_seconds=8,
        database_pool_timeout_seconds=9,
        database_pool_recycle_seconds=120,
    )

    assert database_engine_options(settings) == {
        "pool_pre_ping": True,
        "pool_timeout": 9,
        "pool_recycle": 120,
        "connect_args": {"timeout": 8},
    }
