import pytest

from app.services.router import deterministic_route


@pytest.mark.parametrize(
    ("message", "intent"),
    [
        ("订单 EC2026080001 到哪了", "logistics_query"),
        ("查询订单 EC2026080001", "order_query"),
        ("我要申请退货 EC2026080001", "after_sales"),
        ("能不能退货 EC2026080001", "return_check"),
        ("我要投诉，转人工", "escalate"),
        ("手机无法开机怎么办", "knowledge_query"),
    ],
)
def test_deterministic_route(message: str, intent: str) -> None:
    decision = deterministic_route(message)
    assert decision.intent == intent


def test_router_extracts_only_expected_order_pattern() -> None:
    assert deterministic_route("查 EC2026080001").order_no == "EC2026080001"
    assert deterministic_route("查 2026080001").order_no is None
