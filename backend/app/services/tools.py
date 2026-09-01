from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Conversation
from app.services.knowledge import search_knowledge
from app.services.orders import (
    get_owned_order,
    logistics_payload,
    order_payload,
    return_eligibility,
)


class OrderInput(BaseModel):
    order_no: str = Field(description="EC 开头的订单号")


class KnowledgeInput(BaseModel):
    query: str = Field(description="商品、保修或售后知识问题")


class AfterSalesInput(OrderInput):
    reason: str = Field(description="客户申请售后的原因")


class EscalateInput(BaseModel):
    reason: str = Field(description="转人工原因")


def build_tools(
    session: AsyncSession, customer_id: str, conversation_id: str
) -> dict[str, StructuredTool]:
    # customer_id 由服务端闭包注入，不暴露为模型可填写的工具参数。
    async def get_order(order_no: str) -> dict:
        order = await get_owned_order(session, customer_id, order_no)
        return order_payload(order) if order else {"error": "未找到属于当前客户的订单。"}

    async def get_logistics(order_no: str) -> dict:
        order = await get_owned_order(session, customer_id, order_no)
        return logistics_payload(order) if order else {"error": "未找到属于当前客户的订单。"}

    async def knowledge(query: str) -> dict:
        return {"chunks": await search_knowledge(session, query)}

    async def check_return_eligibility(order_no: str) -> dict:
        order = await get_owned_order(session, customer_id, order_no)
        if not order:
            return {"error": "未找到属于当前客户的订单。"}
        return {**return_eligibility(order), **order_payload(order)}

    async def create_after_sales_request(order_no: str, reason: str) -> dict:
        """只准备售后提案；真正写入必须由图中的人工审批节点执行。"""
        order = await get_owned_order(session, customer_id, order_no)
        if not order:
            return {"error": "未找到属于当前客户的订单。"}
        return {**return_eligibility(order), **order_payload(order), "requested_reason": reason}

    async def escalate_to_human(reason: str) -> dict:
        # 转人工是受控状态变更，后续人工消息仍需客服角色 API 才能写入。
        conversation = await session.get(Conversation, conversation_id)
        conversation.escalated = True
        await session.commit()
        return {"escalated": True, "reason": reason}

    definitions = [
        StructuredTool.from_function(
            coroutine=get_order,
            name="get_order",
            description="查询当前登录客户拥有的订单，不能查询其他客户订单。",
            args_schema=OrderInput,
        ),
        StructuredTool.from_function(
            coroutine=get_logistics,
            name="get_logistics",
            description="查询当前客户订单的物流状态。",
            args_schema=OrderInput,
        ),
        StructuredTool.from_function(
            coroutine=knowledge,
            name="search_knowledge",
            description="检索商品说明、保修和售后政策，返回带来源的 Top 3 片段。",
            args_schema=KnowledgeInput,
        ),
        StructuredTool.from_function(
            coroutine=check_return_eligibility,
            name="check_return_eligibility",
            description="通过确定性规则判断订单能否退货。",
            args_schema=OrderInput,
        ),
        StructuredTool.from_function(
            coroutine=create_after_sales_request,
            name="create_after_sales_request",
            description="准备售后申请；只生成提案，必须经人工审批后才能写入。",
            args_schema=AfterSalesInput,
        ),
        StructuredTool.from_function(
            coroutine=escalate_to_human,
            name="escalate_to_human",
            description="投诉、低置信或信息不足时转人工。",
            args_schema=EscalateInput,
        ),
    ]
    return {tool.name: tool for tool in definitions}
