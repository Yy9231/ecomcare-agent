from functools import lru_cache
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """集中读取环境配置；SecretStr 避免密钥在普通日志和 repr 中直接显示。"""
    app_name: str = "EcomCare Agent"
    database_url: str = "postgresql+asyncpg://ecomcare:ecomcare@localhost:5432/ecomcare"
    checkpoint_database_url: str = "postgresql://ecomcare:ecomcare@localhost:5432/ecomcare"
    jwt_secret: str = "development-only-secret"
    token_minutes: int = 10080
    public_demo_mode: bool = False
    model_enabled: bool = False
    model_provider: str = "openai"
    model_api_key: SecretStr = SecretStr("")
    model_base_url: str = ""
    model_name: str = "gpt-4.1-mini"
    model_provider_configs: SecretStr = SecretStr("")
    model_credentials_secret: SecretStr = SecretStr("")
    model_timeout_seconds: float = 30
    model_max_retries: int = 2
    cors_origins: str = "http://localhost:5173"

    model_config = SettingsConfigDict(env_file="../.env", extra="ignore")

    @property
    def allowed_origins(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def async_database_url(self) -> str:
        """把 Neon 标准连接串转换为 SQLAlchemy asyncpg 可用格式。"""
        parts = urlsplit(self.database_url)
        if parts.scheme in {"postgres", "postgresql"}:
            scheme = "postgresql+asyncpg"
        elif parts.scheme == "postgresql+asyncpg":
            scheme = parts.scheme
        else:
            return self.database_url

        query = []
        has_ssl = False
        for key, value in parse_qsl(parts.query, keep_blank_values=True):
            # asyncpg 使用 ssl 参数，且不识别 Neon libpq 的 channel_binding 参数。
            if key == "channel_binding":
                continue
            if key == "ssl":
                has_ssl = True
            if key == "sslmode":
                if not has_ssl:
                    query.append(("ssl", value))
                    has_ssl = True
                continue
            query.append((key, value))
        return urlunsplit((scheme, parts.netloc, parts.path, urlencode(query), parts.fragment))


@lru_cache
def get_settings() -> Settings:
    """在进程内复用同一份配置，避免每个请求重复解析环境变量。"""
    return Settings()
