import pytest
from pydantic import SecretStr

from app.config import Settings
from app.services import answering
from app.services.answering import deterministic_answer, generate_answer
from app.services.model_gateway import GeneratedText


def model_settings(enabled: bool = True) -> Settings:
    return Settings(
        _env_file=None,
        model_enabled=enabled,
        model_provider="deepseek",
        model_api_key=SecretStr("test-key"),
        model_name="deepseek-chat",
    )


def test_deterministic_logistics_answer() -> None:
    answer = deterministic_answer(
        "logistics_query",
        {
            "order_no": "EC2026080001",
            "carrier": "顺丰",
            "tracking_no": "SF001",
            "status": "shipping",
        },
    )
    assert "运输中" in answer
    assert "SF001" in answer


def test_deterministic_general_chat_answer_identifies_service() -> None:
    answer = deterministic_answer("general_chat", {})
    assert "EcomCare" in answer
    assert "AI 客服" in answer


@pytest.mark.asyncio
async def test_generate_answer_uses_model_after_tool_result(monkeypatch) -> None:
    async def fake_invoke(prompt: str, settings: Settings) -> GeneratedText:
        assert "EC2026080001" in prompt
        assert "不得修改或否认工具结果" in prompt
        return GeneratedText("您的订单正在运输中，请耐心等待。", "deepseek", "deepseek-chat", {"total_tokens": 42})

    monkeypatch.setattr(answering, "invoke_text", fake_invoke)
    result = await generate_answer(
        "订单到哪里了？",
        "logistics_query",
        {"order_no": "EC2026080001", "carrier": "顺丰", "tracking_no": "SF001", "status": "shipping"},
        [],
        [{"role": "user", "content": "订单到哪里了？"}],
        model_settings(),
    )
    assert result.used_model is True
    assert result.content.startswith("您的订单")
    assert result.usage["total_tokens"] == 42


@pytest.mark.asyncio
async def test_generate_answer_falls_back_when_model_fails(monkeypatch) -> None:
    async def fail(*args, **kwargs):
        raise TimeoutError

    monkeypatch.setattr(answering, "invoke_text", fail)
    result = await generate_answer(
        "查询订单",
        "order_query",
        {"order_no": "EC2026080001", "product": "Aurora X1", "status": "delivered"},
        [],
        [],
        model_settings(),
    )
    assert result.used_model is False
    assert result.error == "TimeoutError"
    assert "Aurora X1" in result.content
