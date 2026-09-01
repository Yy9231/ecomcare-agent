import pytest
from pydantic import BaseModel, SecretStr

from app.config import Settings
from app.services import model_gateway
from app.services.model_gateway import PROVIDERS, invoke_structured, resolve_model


def settings_for(provider: str, **overrides) -> Settings:
    values = {
        "model_enabled": True,
        "model_provider": provider,
        "model_api_key": SecretStr("test-key"),
        "model_name": "test-model",
    }
    values.update(overrides)
    return Settings(_env_file=None, **values)


@pytest.mark.parametrize(
    ("provider", "adapter", "base_url", "structured_method"),
    [
        ("openai", "openai", "https://api.openai.com/v1", "json_schema"),
        ("deepseek", "openai", "https://api.deepseek.com", "json_mode"),
        (
            "qwen",
            "openai",
            "https://dashscope.aliyuncs.com/compatible-mode/v1",
            "function_calling",
        ),
        ("anthropic", "anthropic", None, None),
        ("google_genai", "google_genai", None, "json_schema"),
    ],
)
def test_resolve_provider(
    provider: str,
    adapter: str,
    base_url: str | None,
    structured_method: str | None,
) -> None:
    resolved = resolve_model(settings_for(provider))
    assert resolved.adapter == adapter
    assert resolved.base_url == base_url
    assert resolved.structured_method == structured_method


def test_custom_compatible_provider_requires_url() -> None:
    with pytest.raises(ValueError, match="MODEL_BASE_URL"):
        resolve_model(settings_for("openai_compatible"))


def test_ollama_does_not_require_api_key() -> None:
    resolved = resolve_model(
        settings_for("ollama", model_api_key=SecretStr(""), model_name="qwen3:8b")
    )
    assert resolved.base_url == "http://localhost:11434"


def test_unknown_provider_lists_supported_values() -> None:
    with pytest.raises(ValueError, match="Unsupported MODEL_PROVIDER"):
        resolve_model(settings_for("unknown"))


def test_public_status_never_contains_api_key() -> None:
    status = resolve_model(settings_for("openai")).public_status(True)
    assert "api_key" not in status
    assert "test-key" not in str(status)


def test_provider_registry_covers_cloud_and_local_models() -> None:
    assert {"openai", "anthropic", "google_genai", "ollama", "openai_compatible"} <= set(
        PROVIDERS
    )


@pytest.mark.asyncio
async def test_deepseek_thinking_model_uses_json_mode(monkeypatch) -> None:
    class Probe(BaseModel):
        ok: bool

    class FakeStructuredModel:
        async def ainvoke(self, prompt: str) -> dict[str, bool]:
            assert "JSON Schema" in prompt
            return {"ok": True}

    class FakeModel:
        def with_structured_output(self, schema, **kwargs):
            assert schema is Probe
            assert kwargs == {"method": "json_mode"}
            return FakeStructuredModel()

    monkeypatch.setattr(model_gateway, "build_chat_model", lambda settings: FakeModel())
    result = await invoke_structured(
        "返回连接状态",
        Probe,
        settings_for("deepseek", model_name="deepseek-v4-flash"),
    )
    assert result.ok is True
