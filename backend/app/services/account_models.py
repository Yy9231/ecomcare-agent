import base64
import hashlib
import ipaddress
from dataclasses import dataclass
from urllib.parse import urlparse

from cryptography.fernet import Fernet, InvalidToken
from pydantic import SecretStr
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.models import Account, AccountModelConfig
from app.services.model_gateway import PROVIDERS, resolve_model
from app.services.model_preferences import PROVIDER_LABELS, configured_settings, runtime_settings


@dataclass(frozen=True)
class ModelConfigInput:
    provider: str
    model: str | None = None
    base_url: str = ""
    api_key: str = ""


def _fernet(settings: Settings) -> Fernet:
    # 使用独立凭据密钥派生 Fernet key；未配置时仅为本地演示回退到 JWT secret。
    secret = settings.model_credentials_secret.get_secret_value().strip() or settings.jwt_secret
    digest = hashlib.sha256(secret.encode()).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


def encrypt_api_key(api_key: str, settings: Settings | None = None) -> str:
    """加密账号 API Key 后再落库，空值表示不配置个人密钥。"""
    if not api_key:
        return ""
    return _fernet(settings or get_settings()).encrypt(api_key.encode()).decode()


def decrypt_api_key(ciphertext: str, settings: Settings | None = None) -> str:
    """仅在模型调用前解密；解密失败时要求用户重新保存凭据。"""
    if not ciphertext:
        return ""
    try:
        return _fernet(settings or get_settings()).decrypt(ciphertext.encode()).decode()
    except InvalidToken as exc:
        raise ValueError("账号模型凭据无法解密，请重新保存 API Key") from exc


async def _personal_configs(
    session: AsyncSession, account_id: str
) -> dict[str, AccountModelConfig]:
    rows = (
        await session.scalars(
            select(AccountModelConfig).where(AccountModelConfig.account_id == account_id)
        )
    ).all()
    return {item.provider: item for item in rows}


def _candidate_settings(
    config: AccountModelConfig,
    settings: Settings,
    server_settings: dict[str, Settings],
) -> Settings:
    _validate_base_url(config.provider, config.base_url)
    server = server_settings.get(config.provider)
    server_key = resolve_model(server).api_key if server else ""
    return settings.model_copy(
        update={
            "model_enabled": True,
            "model_provider": config.provider,
            "model_name": config.model_name,
            "model_base_url": config.base_url,
            "model_api_key": SecretStr(
                decrypt_api_key(config.api_key_encrypted, settings) or server_key
            ),
        }
    )


def _validate_base_url(provider: str, configured_url: str) -> None:
    """限制云模型访问公网 HTTPS，降低自定义 Base URL 引发的 SSRF 风险。"""
    url = configured_url or PROVIDERS[provider].default_base_url or ""
    if not url:
        return
    parsed = urlparse(url)
    allowed_schemes = {"http", "https"} if provider == "ollama" else {"https"}
    if parsed.scheme not in allowed_schemes or not parsed.hostname:
        raise ValueError("Base URL 必须使用有效的 HTTPS 地址")
    if parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise ValueError("Base URL 不能包含账号、查询参数或片段")
    hostname = parsed.hostname.lower()
    if provider == "ollama":
        return
    if hostname == "localhost" or hostname.endswith((".local", ".internal")):
        raise ValueError("云模型 Base URL 不能指向本机或内部网络")
    try:
        address = ipaddress.ip_address(hostname)
    except ValueError:
        return
    if not address.is_global:
        raise ValueError("云模型 Base URL 不能指向本机或内部网络")


async def account_runtime_settings(
    session: AsyncSession,
    account: Account,
    settings: Settings | None = None,
) -> Settings:
    """按账号选择个人配置、服务端配置或确定性规则模式。"""
    settings = settings or get_settings()
    if settings.public_demo_mode:
        return settings.model_copy(update={"model_enabled": False})
    provider = (account.model_provider or "").strip().lower()
    if provider == "deterministic":
        return settings.model_copy(update={"model_enabled": False})
    personal = await session.scalar(
        select(AccountModelConfig).where(
            AccountModelConfig.account_id == account.id,
            AccountModelConfig.provider == provider,
        )
    )
    if personal:
        candidate = _candidate_settings(personal, settings, configured_settings(settings))
        resolve_model(candidate)
        return candidate
    try:
        return runtime_settings(provider or None, settings)
    except ValueError as exc:
        raise ValueError("当前账号的模型配置不完整，请先在界面中保存") from exc


async def account_runtime_settings_by_id(
    session: AsyncSession,
    account_id: str,
    settings: Settings | None = None,
) -> Settings:
    account = await session.get(Account, account_id)
    if not account or not account.active:
        raise ValueError("账号已失效")
    return await account_runtime_settings(session, account, settings)


async def model_preferences(
    session: AsyncSession,
    account: Account,
    settings: Settings | None = None,
    personal_configs: dict[str, AccountModelConfig] | None = None,
) -> dict:
    """返回可公开的模型状态；永不把已保存 API Key 明文传回前端。"""
    settings = settings or get_settings()
    rule_option = {
        "provider": "deterministic",
        "label": "规则模式（公开演示）" if settings.public_demo_mode else "规则模式",
        "model": None,
        "base_url": "",
        "default_base_url": None,
        "requires_api_key": False,
        "configured": True,
        "has_api_key": False,
        "source": "rule",
    }
    if settings.public_demo_mode:
        return {"selected": rule_option, "options": [rule_option]}
    personal = personal_configs
    if personal is None:
        personal = await _personal_configs(session, account.id)
    server = configured_settings(settings)
    options: list[dict] = [rule_option]
    for provider, spec in PROVIDERS.items():
        own = personal.get(provider)
        server_config = server.get(provider)
        resolved_server = resolve_model(server_config) if server_config else None
        options.append(
            {
                "provider": provider,
                "label": PROVIDER_LABELS.get(provider, provider),
                "model": own.model_name if own else resolved_server.model if resolved_server else None,
                "base_url": own.base_url if own else resolved_server.base_url if resolved_server else "",
                "default_base_url": spec.default_base_url,
                "requires_api_key": spec.api_key_required,
                "configured": bool(own or server_config),
                "has_api_key": bool(own and own.api_key_encrypted) or bool(resolved_server and resolved_server.api_key),
                "source": "account" if own else "server" if server_config else "none",
            }
        )
    selected_provider = account.model_provider or (
        settings.model_provider if settings.model_enabled else "deterministic"
    )
    selected = next(
        (item for item in options if item["provider"] == selected_provider), options[0]
    )
    return {"selected": selected, "options": options}


async def save_model_config(
    session: AsyncSession,
    account: Account,
    payload: ModelConfigInput,
    settings: Settings | None = None,
) -> dict:
    """校验并保存账号级模型配置，留空 API Key 时保留原密钥。"""
    settings = settings or get_settings()
    provider = payload.provider.strip().lower()
    if settings.public_demo_mode and provider != "deterministic":
        raise ValueError("公开演示环境已锁定规则模式")
    if provider == "deterministic":
        personal = await _personal_configs(session, account.id)
        account.model_provider = provider
        account.model_name = None
        await session.commit()
        return await model_preferences(session, account, settings, personal)
    if provider not in PROVIDERS:
        raise ValueError("不支持该模型供应商")
    model = (payload.model or "").strip()
    if not model:
        raise ValueError("Model 不能为空")
    personal = await _personal_configs(session, account.id)
    existing = personal.get(provider)
    encrypted = existing.api_key_encrypted if existing else ""
    if payload.api_key.strip():
        encrypted = encrypt_api_key(payload.api_key.strip(), settings)
    record = existing or AccountModelConfig(account_id=account.id, provider=provider)
    record.model_name = model
    record.base_url = payload.base_url.strip().rstrip("/")
    record.api_key_encrypted = encrypted
    candidate = _candidate_settings(record, settings, configured_settings(settings))
    resolve_model(candidate)
    session.add(record)
    personal[provider] = record
    account.model_provider = provider
    account.model_name = model
    await session.commit()
    return await model_preferences(session, account, settings, personal)
