from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

from app.models import Order
from app.seed import refresh_demo_order
from app.services.embeddings import HashingEmbedder
from app.services.orders import return_eligibility
from app.services.tools import build_tools


def test_return_within_seven_days_is_eligible() -> None:
    now = datetime.now(UTC)
    order = SimpleNamespace(status="delivered", delivered_at=now - timedelta(days=6))
    assert return_eligibility(order, now)["eligible"] is True


def test_return_after_seven_days_is_rejected() -> None:
    now = datetime.now(UTC)
    order = SimpleNamespace(status="delivered", delivered_at=now - timedelta(days=8))
    assert return_eligibility(order, now)["eligible"] is False


def test_shipping_order_cannot_be_returned() -> None:
    order = SimpleNamespace(status="shipping", delivered_at=None)
    assert return_eligibility(order)["eligible"] is False


def test_fixed_demo_order_is_refreshed_inside_return_window() -> None:
    now = datetime(2026, 9, 7, tzinfo=UTC)
    order = Order(
        order_no="EC2026080001",
        customer_id="CUST-001",
        product_id="PROD-001",
        status="delivered",
        amount=336,
        purchased_at=now - timedelta(days=40),
        delivered_at=now - timedelta(days=30),
    )
    refresh_demo_order(order, now)
    assert return_eligibility(order, now)["eligible"] is True
    assert order.delivered_at == now - timedelta(days=3)


def test_hash_embedding_is_repeatable_and_normalized() -> None:
    embedder = HashingEmbedder()
    first = embedder.embed("七天无理由退货")
    assert first == embedder.embed("七天无理由退货")
    assert len(first) == 1536
    assert abs(sum(value * value for value in first) - 1) < 1e-8


def test_tool_catalog_has_six_typed_tools_without_customer_id() -> None:
    tools = build_tools(object(), "CUST-001", "conversation-1")  # type: ignore[arg-type]
    assert set(tools) == {
        "get_order",
        "get_logistics",
        "search_knowledge",
        "check_return_eligibility",
        "create_after_sales_request",
        "escalate_to_human",
    }
    assert all("customer_id" not in tool.args for tool in tools.values())
