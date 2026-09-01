import json

import pytest
from pydantic import SecretStr

from app.config import Settings
from app.services.model_preferences import list_options, runtime_settings, selected_option


def configured_settings() -> Settings:
    extra = {
        "openai": {"api_key": "openai-secret", "model": "gpt-test"},
        "ollama": {"model": "qwen3:8b", "base_url": "http://ollama:11434"},
    }
    return Settings(
        _env_file=None,
        model_enabled=True,
        model_provider="deepseek",
        model_api_key=SecretStr("deepseek-secret"),
        model_name="deepseek-chat",
        model_provider_configs=SecretStr(json.dumps(extra)),
    )


def test_options_only_enable_server_configured_providers() -> None:
    options = {item.provider: item for item in list_options(configured_settings())}
    assert options["deterministic"].available is True
    assert options["deepseek"].model == "deepseek-chat"
    assert options["openai"].model == "gpt-test"
    assert options["ollama"].available is True
    assert options["anthropic"].available is False
    assert "secret" not in str([item.public() for item in options.values()])


def test_runtime_settings_uses_selected_provider_credentials() -> None:
    runtime = runtime_settings("openai", configured_settings())
    assert runtime.model_provider == "openai"
    assert runtime.model_name == "gpt-test"
    assert runtime.model_api_key.get_secret_value() == "openai-secret"


def test_rule_mode_disables_external_model() -> None:
    assert runtime_settings("deterministic", configured_settings()).model_enabled is False


def test_unconfigured_provider_is_rejected() -> None:
    with pytest.raises(ValueError, match="not configured"):
        runtime_settings("anthropic", configured_settings())


def test_removed_account_provider_falls_back_to_rule_mode() -> None:
    assert selected_option("anthropic", configured_settings()).provider == "deterministic"


def test_invalid_provider_json_is_rejected() -> None:
    settings = configured_settings().model_copy(
        update={"model_provider_configs": SecretStr("not-json")}
    )
    with pytest.raises(ValueError, match="valid JSON"):
        list_options(settings)
