import pytest

from app.config import Settings
from app.services import router
from app.services.router import deterministic_route, route_message


@pytest.mark.parametrize(
    ("message", "intent"),
    [
        ("订单 EC2026080001 到哪了", "logistics_query"),
        ("查询订单 EC2026080001", "order_query"),
        ("我要申请退货 EC2026080001", "after_sales"),
        ("能不能退货 EC2026080001", "return_check"),
        ("我要投诉，转人工", "escalate"),
        ("手机无法开机怎么办", "knowledge_query"),
        ("你好你是谁", "general_chat"),
        ("谢谢你的帮助", "general_chat"),
        ("shipping status", "knowledge_query"),
        ("你好，查询订单 EC2026080001", "order_query"),
    ],
)
def test_deterministic_route(message: str, intent: str) -> None:
    decision = deterministic_route(message)
    assert decision.intent == intent


def test_router_extracts_only_expected_order_pattern() -> None:
    assert deterministic_route("查 EC2026080001").order_no == "EC2026080001"
    assert deterministic_route("查 2026080001").order_no is None


@pytest.mark.asyncio
async def test_greeting_bypasses_model_router(monkeypatch) -> None:
    async def unexpected_model_call(*args, **kwargs):
        raise AssertionError("普通问候不应交给模型决定是否转人工")

    monkeypatch.setattr(router, "invoke_structured", unexpected_model_call)
    decision = await route_message(
        "你好，你是谁？",
        Settings(_env_file=None, model_enabled=True),
    )
    assert decision.intent == "general_chat"
