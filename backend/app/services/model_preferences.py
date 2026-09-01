import json
from dataclasses import dataclass

from pydantic import SecretStr

from app.config import Settings, get_settings
from app.services.model_gateway import PROVIDERS, resolve_model

PROVIDER_LABELS = {
    "openai": "OpenAI",
    "azure_openai": "Azure OpenAI",
    "deepseek": "DeepSeek",
    "qwen": "通义千问",
    "moonshot": "Kimi",
    "zhipu": "智谱 GLM",
    "doubao": "豆包",
    "siliconflow": "硅基流动",
    "openrouter": "OpenRouter",
    "groq": "Groq",
    "xai": "xAI",
    "mistral": "Mistral",
    "openai_compatible": "OpenAI-compatible",
    "anthropic": "Anthropic Claude",
    "google_genai": "Google Gemini",
    "ollama": "本地 Ollama",
}


@dataclass(frozen=True)
class ModelOption:
    provider: str
    label: str
    model: str | None
    available: bool

    def public(self) -> dict[str, str | bool | None]:
        return {
            "provider": self.provider,
            "label": self.label,
            "model": self.model,
            "available": self.available,
        }


def _extra_configs(settings: Settings) -> dict[str, dict[str, str]]:
    raw = settings.model_provider_configs.get_secret_value().strip()
    if not raw:
        return {}
    try:
        value = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError("MODEL_PROVIDER_CONFIGS must be valid JSON") from exc
    if not isinstance(value, dict):
        raise TypeError("MODEL_PROVIDER_CONFIGS must be a JSON object")
    return {
        str(provider).strip().lower(): config
        for provider, config in value.items()
        if isinstance(config, dict)
    }


def configured_settings(settings: Settings | None = None) -> dict[str, Settings]:
    """合并主模型与 JSON 中的额外服务端配置，并在启动使用前完成校验。"""
    settings = settings or get_settings()
    configured: dict[str, Settings] = {}
    if settings.model_enabled:
        resolved = resolve_model(settings)
        configured[resolved.provider] = settings
    for provider, config in _extra_configs(settings).items():
        if provider not in PROVIDERS:
            continue
        candidate = settings.model_copy(
            update={
                "model_enabled": True,
                "model_provider": provider,
                "model_api_key": SecretStr(str(config.get("api_key", ""))),
                "model_base_url": str(config.get("base_url", "")),
                "model_name": str(config.get("model", "")),
            }
        )
        resolve_model(candidate)
        configured[provider] = candidate
    return configured


def list_options(settings: Settings | None = None) -> list[ModelOption]:
    configured = configured_settings(settings)
    options = [ModelOption("deterministic", "规则模式", None, True)]
    options.extend(
        ModelOption(
            provider,
            PROVIDER_LABELS.get(provider, provider),
            resolve_model(configured[provider]).model if provider in configured else None,
            provider in configured,
        )
        for provider in PROVIDERS
    )
    return options


def runtime_settings(provider: str | None, settings: Settings | None = None) -> Settings:
    """选择服务端 Provider；不可用时明确报错而不是静默切换模型。"""
    settings = settings or get_settings()
    requested = (provider or "").strip().lower()
    if requested == "deterministic":
        return settings.model_copy(update={"model_enabled": False})
    configured = configured_settings(settings)
    if requested:
        if requested not in configured:
            raise ValueError(f"Model provider '{requested}' is not configured")
        return configured[requested]
    if settings.model_enabled:
        return settings
    return settings.model_copy(update={"model_enabled": False})


def selected_option(provider: str | None, settings: Settings | None = None) -> ModelOption:
    settings = settings or get_settings()
    requested = (
        provider.strip().lower()
        if provider
        else settings.model_provider.strip().lower()
        if settings.model_enabled
        else "deterministic"
    )
    options = {item.provider: item for item in list_options(settings)}
    selected = options.get(requested)
    if selected and selected.available:
        return selected
    return options["deterministic"]
