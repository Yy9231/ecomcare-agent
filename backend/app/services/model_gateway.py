import json
from dataclasses import dataclass
from typing import Literal

from langchain_core.language_models.chat_models import BaseChatModel
from pydantic import BaseModel

from app.config import Settings, get_settings

AdapterName = Literal["openai", "anthropic", "google_genai", "ollama"]
StructuredMethod = Literal["json_schema", "function_calling", "json_mode"]


@dataclass(frozen=True)
class ProviderSpec:
    adapter: AdapterName
    default_base_url: str | None = None
    api_key_required: bool = True
    structured_method: StructuredMethod | None = None


@dataclass(frozen=True)
class ResolvedModel:
    provider: str
    adapter: AdapterName
    model: str
    api_key: str
    base_url: str | None
    timeout_seconds: float
    max_retries: int
    structured_method: StructuredMethod | None

    def public_status(self, enabled: bool) -> dict[str, str | bool | float | int | None]:
        return {
            "enabled": enabled,
            "provider": self.provider,
            "adapter": self.adapter,
            "model": self.model,
            "base_url": self.base_url,
            "timeout_seconds": self.timeout_seconds,
            "max_retries": self.max_retries,
            "structured_method": self.structured_method,
        }


@dataclass(frozen=True)
class GeneratedText:
    content: str
    provider: str
    model: str
    usage: dict[str, int]


PROVIDERS: dict[str, ProviderSpec] = {
    # 多数厂商复用 OpenAI 协议；Claude、Gemini、Ollama 使用各自原生适配器。
    "openai": ProviderSpec("openai", "https://api.openai.com/v1", structured_method="json_schema"),
    "azure_openai": ProviderSpec("openai", structured_method="json_schema"),
    "deepseek": ProviderSpec(
        "openai", "https://api.deepseek.com", structured_method="json_mode"
    ),
    "qwen": ProviderSpec(
        "openai",
        "https://dashscope.aliyuncs.com/compatible-mode/v1",
        structured_method="function_calling",
    ),
    "moonshot": ProviderSpec(
        "openai", "https://api.moonshot.cn/v1", structured_method="function_calling"
    ),
    "zhipu": ProviderSpec(
        "openai", "https://open.bigmodel.cn/api/paas/v4", structured_method="function_calling"
    ),
    "doubao": ProviderSpec(
        "openai",
        "https://ark.cn-beijing.volces.com/api/v3",
        structured_method="function_calling",
    ),
    "siliconflow": ProviderSpec(
        "openai", "https://api.siliconflow.cn/v1", structured_method="function_calling"
    ),
    "openrouter": ProviderSpec(
        "openai", "https://openrouter.ai/api/v1", structured_method="function_calling"
    ),
    "groq": ProviderSpec(
        "openai", "https://api.groq.com/openai/v1", structured_method="function_calling"
    ),
    "xai": ProviderSpec(
        "openai", "https://api.x.ai/v1", structured_method="function_calling"
    ),
    "mistral": ProviderSpec(
        "openai", "https://api.mistral.ai/v1", structured_method="function_calling"
    ),
    "openai_compatible": ProviderSpec("openai", structured_method="function_calling"),
    "anthropic": ProviderSpec("anthropic"),
    "google_genai": ProviderSpec("google_genai", structured_method="json_schema"),
    "ollama": ProviderSpec("ollama", "http://localhost:11434", False),
}


def resolve_model(settings: Settings | None = None) -> ResolvedModel:
    """把环境或账号配置解析为统一且完整的运行时模型描述。"""
    settings = settings or get_settings()
    provider = settings.model_provider.strip().lower()
    spec = PROVIDERS.get(provider)
    if spec is None:
        supported = ", ".join(sorted(PROVIDERS))
        raise ValueError(f"Unsupported MODEL_PROVIDER '{provider}'. Supported: {supported}")

    model = settings.model_name.strip()
    if not model:
        raise ValueError("MODEL_NAME is required when MODEL_ENABLED=true")

    api_key = settings.model_api_key.get_secret_value().strip()
    if spec.api_key_required and not api_key:
        raise ValueError(f"MODEL_API_KEY is required for provider '{provider}'")

    configured_url = settings.model_base_url.strip().rstrip("/")
    base_url = configured_url or spec.default_base_url
    if spec.adapter in ("openai", "ollama") and not base_url:
        raise ValueError(f"MODEL_BASE_URL is required for provider '{provider}'")

    return ResolvedModel(
        provider=provider,
        adapter=spec.adapter,
        model=model,
        api_key=api_key,
        base_url=base_url,
        timeout_seconds=settings.model_timeout_seconds,
        max_retries=settings.model_max_retries,
        structured_method=spec.structured_method,
    )


def build_chat_model(settings: Settings | None = None) -> BaseChatModel:
    """根据适配器构造 LangChain ChatModel，业务层无需感知厂商 SDK。"""
    config = resolve_model(settings)
    common = {
        "model": config.model,
        "temperature": 0,
        "timeout": config.timeout_seconds,
        "max_retries": config.max_retries,
    }

    if config.adapter == "openai":
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(api_key=config.api_key, base_url=config.base_url, **common)
    if config.adapter == "anthropic":
        from langchain_anthropic import ChatAnthropic

        extra = {"base_url": config.base_url} if config.base_url else {}
        return ChatAnthropic(api_key=config.api_key, **common, **extra)
    if config.adapter == "google_genai":
        from langchain_google_genai import ChatGoogleGenerativeAI

        return ChatGoogleGenerativeAI(api_key=config.api_key, **common)

    from langchain_ollama import ChatOllama

    return ChatOllama(base_url=config.base_url, **common)


async def invoke_structured[SchemaT: BaseModel](
    prompt: str,
    schema: type[SchemaT],
    settings: Settings | None = None,
) -> SchemaT:
    """按供应商能力选择结构化输出方式，并统一通过 Pydantic 校验。"""
    config = resolve_model(settings)
    model = build_chat_model(settings)
    invocation_prompt = prompt
    if config.structured_method == "json_mode":
        schema_json = json.dumps(schema.model_json_schema(), ensure_ascii=False)
        invocation_prompt = (
            f"{prompt}\n只返回符合以下 JSON Schema 的 JSON 对象，不要使用 Markdown：\n{schema_json}"
        )
    if config.adapter == "google_genai":
        structured = model.with_structured_output(
            schema.model_json_schema(), method="json_schema"
        )
    elif config.structured_method:
        structured = model.with_structured_output(schema, method=config.structured_method)
    else:
        structured = model.with_structured_output(schema)
    result = await structured.ainvoke(invocation_prompt)
    return result if isinstance(result, schema) else schema.model_validate(result)


def _text_content(content: str | list) -> str:
    if isinstance(content, str):
        return content.strip()
    parts = [
        str(block.get("text", ""))
        for block in content
        if isinstance(block, dict) and block.get("type") == "text"
    ]
    return "".join(parts).strip()


async def invoke_text(prompt: str, settings: Settings | None = None) -> GeneratedText:
    """执行文本生成，并只暴露可用于审计的标准 Token 字段。"""
    config = resolve_model(settings)
    response = await build_chat_model(settings).ainvoke(prompt)
    content = _text_content(response.content)
    if not content:
        raise ValueError("Model returned an empty response")
    raw_usage = response.usage_metadata or {}
    usage = {
        key: int(value)
        for key, value in raw_usage.items()
        if isinstance(value, int) and key in {"input_tokens", "output_tokens", "total_tokens"}
    }
    return GeneratedText(content, config.provider, config.model, usage)
