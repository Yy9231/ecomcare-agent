import time
import uuid
from typing import Annotated, TypedDict

from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.types import Command, interrupt

from app.database import SessionLocal
from app.models import Order, ToolTrace
from app.services.account_models import account_runtime_settings_by_id
from app.services.answering import generate_answer
from app.services.orders import create_after_sales
from app.services.router import route_message
from app.services.tools import build_tools


class AgentState(TypedDict, total=False):
    """跨节点传递并由 checkpoint 持久化的最小工作流状态。"""
    messages: Annotated[list, add_messages]
    customer_id: str
    conversation_id: str
    user_message: str
    intent: str
    order_no: str | None
    reason: str | None
    tool_name: str
    tool_result: dict
    answer: str | None
    references: list[dict]
    idempotency_key: str
    model_provider: str | None
    model_name: str | None
    model_used: bool
    requesting_account_id: str


async def _account_settings(state: AgentState):
    # checkpoint 只保存账号 ID，运行时再取密钥，避免凭据进入图状态快照。
    async with SessionLocal() as session:
        return await account_runtime_settings_by_id(session, state["requesting_account_id"])


async def route_node(state: AgentState) -> dict:
    """识别意图并为本轮写操作生成稳定的幂等键。"""
    settings = await _account_settings(state)
    decision = await route_message(state["user_message"], settings)
    return {
        "intent": decision.intent,
        "order_no": decision.order_no,
        "reason": decision.reason,
        "idempotency_key": f"{state['conversation_id']}:{uuid.uuid5(uuid.NAMESPACE_URL, state['user_message'])}",
        "answer": None,
        "model_provider": None,
        "model_name": None,
        "model_used": False,
    }


async def _trace(conversation_id: str, name: str, started: float, output: dict) -> None:
    """将工具或模型调用结果独立落库，供工作台审计和指标聚合。"""
    async with SessionLocal() as session:
        session.add(
            ToolTrace(
                conversation_id=conversation_id,
                tool_name=name,
                success="error" not in output,
                output_data=output,
                duration_ms=int((time.perf_counter() - started) * 1000),
            )
        )
        await session.commit()


async def tool_node(state: AgentState) -> dict:
    """把意图映射到窄接口工具，并记录引用和执行轨迹。"""
    started = time.perf_counter()
    intent = state["intent"]
    name = {
        "order_query": "get_order",
        "logistics_query": "get_logistics",
        "knowledge_query": "search_knowledge",
        "return_check": "check_return_eligibility",
        "after_sales": "create_after_sales_request",
        "escalate": "escalate_to_human",
    }[intent]
    references: list[dict] = []
    async with SessionLocal() as session:
        tools = build_tools(session, state["customer_id"], state["conversation_id"])
        if intent not in {"knowledge_query", "escalate"} and not state.get("order_no"):
            result = {"error": "请提供 EC 开头的订单号。"}
        else:
            arguments = {"order_no": state["order_no"]}
            if intent == "knowledge_query":
                arguments = {"query": state["user_message"]}
            elif intent == "escalate":
                arguments = {"reason": state["user_message"]}
            elif intent == "after_sales":
                arguments["reason"] = state.get("reason") or "用户申请售后"
            result = await tools[name].ainvoke(arguments)
            references = result.get("chunks", [])
    await _trace(state["conversation_id"], name, started, result)
    return {"tool_name": name, "tool_result": result, "references": references}


def approval_route(state: AgentState) -> str:
    # 只有“售后申请且资格通过”才进入人工审批，其余请求直接生成回答。
    result = state.get("tool_result", {})
    return "approval" if state["intent"] == "after_sales" and result.get("eligible") else "final"


async def approval_node(state: AgentState) -> dict:
    """暂停高风险写操作；客服恢复后才幂等创建售后单。"""
    proposal = {
        "conversation_id": state["conversation_id"],
        "customer_id": state["customer_id"],
        "order_id": state["tool_result"]["order_id"],
        "order_no": state["tool_result"]["order_no"],
        "reason": state.get("reason") or "用户申请售后",
        "idempotency_key": state["idempotency_key"],
    }
    decision = interrupt(proposal)
    if decision.get("decision") != "approve":
        return {"answer": "售后申请未获批准，客服备注：" + decision.get("note", "无")}
    async with SessionLocal() as session:
        order = await session.get(Order, proposal["order_id"])
        request = await create_after_sales(
            session, order, proposal["reason"], proposal["idempotency_key"]
        )
    return {"answer": f"售后申请已创建，申请编号：{request.id}。"}


async def final_node(state: AgentState) -> dict:
    """优先返回审批结论，否则使用账号模型依据工具结果组织回答。"""
    if state.get("answer"):
        return {"messages": [{"role": "assistant", "content": state["answer"]}]}
    started = time.perf_counter()
    response = await generate_answer(
        state["user_message"],
        state["intent"],
        state.get("tool_result", {}),
        state.get("references", []),
        state.get("messages", []),
        await _account_settings(state),
    )
    if response.provider:
        trace_output: dict = {
            "provider": response.provider,
            "model": response.model,
            "usage": response.usage,
            "fallback": not response.used_model,
        }
        if response.error:
            trace_output["error"] = response.error
        await _trace(state["conversation_id"], "llm_generate", started, trace_output)
    return {
        "answer": response.content,
        "messages": [{"role": "assistant", "content": response.content}],
        "model_provider": response.provider,
        "model_name": response.model,
        "model_used": response.used_model,
    }


def build_graph(checkpointer):
    """构建 route → tool → approval/final 的单 Agent 显式状态机。"""
    builder = StateGraph(AgentState)
    builder.add_node("route", route_node)
    builder.add_node("tool", tool_node)
    builder.add_node("approval", approval_node)
    builder.add_node("final", final_node)
    builder.add_edge(START, "route")
    builder.add_edge("route", "tool")
    builder.add_conditional_edges("tool", approval_route, {"approval": "approval", "final": "final"})
    builder.add_edge("approval", "final")
    builder.add_edge("final", END)
    return builder.compile(checkpointer=checkpointer)


async def resume_graph(graph, conversation_id: str, decision: dict) -> dict:
    """按 conversation_id 找回 checkpoint，并把客服决定送回中断点。"""
    return await graph.ainvoke(
        Command(resume=decision), config={"configurable": {"thread_id": conversation_id}}
    )
