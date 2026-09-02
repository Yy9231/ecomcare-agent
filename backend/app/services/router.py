import re

from app.config import Settings, get_settings
from app.schemas import RouteDecision
from app.services.model_gateway import invoke_structured

ORDER_PATTERN = re.compile(r"EC\d{10}")
GENERAL_CHAT_TERMS = (
    "你好",
    "您好",
    "你是谁",
    "你叫什么",
    "介绍一下你自己",
    "你能做什么",
    "谢谢",
    "感谢",
    "再见",
)
ENGLISH_GREETING_PATTERN = re.compile(r"\b(?:hello|hi)\b", re.IGNORECASE)


def _is_general_chat(message: str) -> bool:
    """识别无需查询业务数据的寒暄，避免模型误触发转人工。"""
    lowered = message.strip().lower()
    return any(term in lowered for term in GENERAL_CHAT_TERMS) or bool(
        ENGLISH_GREETING_PATTERN.search(lowered)
    )


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
    elif _is_general_chat(message):
        intent = "general_chat"
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
    baseline = deterministic_route(message)
    # 寒暄由服务端确定性识别，不能让模型把“你好”误判成高成本的人工转接。
    if not settings.model_enabled or baseline.intent == "general_chat":
        return baseline
    return await invoke_structured(
        "你是3C商城客服路由器。只选择一个最匹配的意图，不得编造订单号。\n"
        "意图定义：order_query=查询订单；logistics_query=查询物流；"
        "knowledge_query=商品、保修或政策知识；return_check=判断能否退货；"
        "after_sales=明确要求创建退货或售后申请；general_chat=问候、自我介绍、感谢等普通对话；"
        "escalate=用户明确要求真人客服、投诉或要求经理介入。"
        "普通问候和一般问题不得选择 escalate。\n"
        f"用户消息：{message}",
        RouteDecision,
        settings,
    )
