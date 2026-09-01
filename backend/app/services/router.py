import re

from app.config import Settings, get_settings
from app.schemas import RouteDecision
from app.services.model_gateway import invoke_structured

ORDER_PATTERN = re.compile(r"EC\d{10}")


def deterministic_route(message: str) -> RouteDecision:
    """无外部模型时提供可重复的意图基线，也作为演示降级路径。"""
    order_match = ORDER_PATTERN.search(message.upper())
    order_no = order_match.group(0) if order_match else None
    lowered = message.lower()
    after_sales_action = any(
        word in lowered
        for word in ("申请退", "申请售后", "售后申请", "直接退", "直接给", "我要退", "帮我退")
    )
    if after_sales_action:
        intent = "after_sales"
    elif any(word in lowered for word in ("人工", "投诉", "经理")):
        intent = "escalate"
    elif "退款到账" in lowered:
        intent = "knowledge_query"
    elif any(word in lowered for word in ("可以退", "能不能退", "能退", "退吗", "退货条件", "退货期")):
        intent = "return_check"
    elif any(word in lowered for word in ("物流", "快递", "运单", "到哪", "送达", "在哪里")):
        intent = "logistics_query"
    elif order_no or any(word in lowered for word in ("订单", "购买")):
        intent = "order_query"
    else:
        intent = "knowledge_query"
    return RouteDecision(
        intent=intent,
        order_no=order_no,
        reason=message if intent == "after_sales" else None,
        confidence=0.9 if intent != "knowledge_query" else 0.75,
    )


async def route_message(message: str, settings: Settings | None = None) -> RouteDecision:
    """按当前账号配置选择规则路由或受 Pydantic 约束的模型路由。"""
    settings = settings or get_settings()
    if not settings.model_enabled:
        return deterministic_route(message)
    return await invoke_structured(
        "你是3C商城客服路由器。只选择一个最匹配的意图，不得编造订单号。\n"
        f"用户消息：{message}",
        RouteDecision,
        settings,
    )
