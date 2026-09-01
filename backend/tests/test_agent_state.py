import pytest

from app.config import Settings
from app.schemas import RouteDecision
from app.services import agent


@pytest.mark.asyncio
async def test_route_node_clears_previous_turn_output(monkeypatch) -> None:
    async def fake_route(message: str, settings=None) -> RouteDecision:
        return RouteDecision(
            intent="knowledge_query",
            order_no=None,
            reason=None,
            confidence=0.98,
        )

    async def fake_account_settings(state) -> Settings:
        return Settings(_env_file=None, model_enabled=False)

    monkeypatch.setattr(agent, "route_message", fake_route)
    monkeypatch.setattr(agent, "_account_settings", fake_account_settings)
    update = await agent.route_node(
        {
            "conversation_id": "conversation-1",
            "customer_id": "customer-1",
            "user_message": "手机无法开机怎么办？",
            "requesting_account_id": "account-1",
            "answer": "未找到属于当前客户的订单。",
            "model_provider": "deepseek",
            "model_name": "deepseek-v4-flash",
            "model_used": False,
        }
    )
    assert update["answer"] is None
    assert update["model_provider"] is None
    assert update["model_name"] is None
    assert update["model_used"] is False
