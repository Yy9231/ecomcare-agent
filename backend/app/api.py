import json
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from langgraph.types import Command
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.models import Account, Approval, Conversation, Message, ToolTrace
from app.schemas import (
    ApprovalDecision,
    HumanReplyRequest,
    MessageRequest,
)
from app.security import current_identity, require_agent, require_customer
from app.services.conversations import (
    create_human_message,
    list_conversation_summaries,
    mark_agent_read,
)

router = APIRouter(prefix="/api/v1")


def serialize_sse(event: str, data: dict) -> str:
    """按浏览器 EventSource 兼容格式序列化单个 SSE 事件。"""
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


@router.post("/conversations")
async def create_conversation(
    identity: dict = Depends(require_customer), session: AsyncSession = Depends(get_session)
) -> dict:
    conversation = Conversation(customer_id=identity["customer_id"])
    session.add(conversation)
    await session.commit()
    await session.refresh(conversation)
    return {"id": conversation.id, "status": conversation.status}


@router.get("/conversations")
async def list_conversations(
    identity: dict = Depends(current_identity), session: AsyncSession = Depends(get_session)
) -> list[dict]:
    return await list_conversation_summaries(session, identity)


async def _owned_conversation(
    session: AsyncSession, conversation_id: str, identity: dict
) -> Conversation:
    """客服可访问全部会话，客户只能访问属于自己的会话。"""
    conversation = await session.get(Conversation, conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    if identity["role"] != "agent" and conversation.customer_id != identity["customer_id"]:
        raise HTTPException(status_code=403, detail="Conversation access denied")
    return conversation


@router.post("/conversations/{conversation_id}/read")
async def mark_conversation_read(
    conversation_id: str,
    identity: dict = Depends(require_agent),
    session: AsyncSession = Depends(get_session),
) -> dict:
    conversation = await _owned_conversation(session, conversation_id, identity)
    read_at = await mark_agent_read(session, conversation)
    return {"conversation_id": conversation.id, "read_at": read_at.isoformat()}


@router.get("/conversations/{conversation_id}")
async def get_conversation(
    conversation_id: str,
    identity: dict = Depends(current_identity),
    session: AsyncSession = Depends(get_session),
) -> dict:
    conversation = await _owned_conversation(session, conversation_id, identity)
    messages = (
        await session.scalars(
            select(Message).where(Message.conversation_id == conversation_id).order_by(Message.created_at)
        )
    ).all()
    traces = (
        await session.scalars(
            select(ToolTrace).where(ToolTrace.conversation_id == conversation_id).order_by(ToolTrace.created_at)
        )
    ).all()
    latest_approval = await session.scalar(
        select(Approval)
        .where(Approval.conversation_id == conversation_id)
        .order_by(Approval.created_at.desc())
        .limit(1)
    )
    return {
        "id": conversation.id,
        "customer_id": conversation.customer_id,
        "status": conversation.status,
        "escalated": conversation.escalated,
        "messages": [
            {
                "id": item.id,
                "role": item.role,
                "content": item.content,
                "references": item.references,
                "created_at": item.created_at.isoformat(),
            }
            for item in messages
        ],
        "latest_approval": {
            "id": latest_approval.id,
            "status": latest_approval.status,
            "decided_at": latest_approval.decided_at.isoformat() if latest_approval.decided_at else None,
        }
        if latest_approval
        else None,
        "traces": [
            {
                "id": item.id,
                "tool_name": item.tool_name,
                "success": item.success,
                "duration_ms": item.duration_ms,
                "output": item.output_data,
            }
            for item in traces
        ],
    }


@router.post("/conversations/{conversation_id}/messages/stream")
async def stream_message(
    conversation_id: str,
    payload: MessageRequest,
    request: Request,
    identity: dict = Depends(current_identity),
    session: AsyncSession = Depends(get_session),
) -> StreamingResponse:
    await _owned_conversation(session, conversation_id, identity)
    account = await session.get(Account, identity["account_id"])
    if not account or not account.active:
        raise HTTPException(status_code=401, detail="账号已失效")
    session.add(Message(conversation_id=conversation_id, role="user", content=payload.content))
    await session.commit()

    async def events():
        try:
            # conversation_id 同时作为 LangGraph thread_id，用于中断后的准确恢复。
            graph = request.app.state.agent_graph
            result = await graph.ainvoke(
                {
                    "customer_id": identity["customer_id"],
                    "conversation_id": conversation_id,
                    "user_message": payload.content,
                    "requesting_account_id": account.id,
                    "messages": [{"role": "user", "content": payload.content}],
                },
                config={"configurable": {"thread_id": conversation_id}},
            )
            yield serialize_sse("tool_started", {"name": result.get("tool_name", "agent")})
            yield serialize_sse("tool_finished", {"result": result.get("tool_result", {})})
            interrupts = result.get("__interrupt__", [])
            if interrupts:
                # interrupt 提案幂等落库；重复请求不会生成多张待审批单。
                proposal = interrupts[0].value
                async with request.app.state.session_factory() as approval_session:
                    existing = await approval_session.scalar(
                        select(Approval).where(Approval.idempotency_key == proposal["idempotency_key"])
                    )
                    approval = existing or Approval(
                        conversation_id=proposal["conversation_id"],
                        customer_id=proposal["customer_id"],
                        order_id=proposal["order_id"],
                        action="create_after_sales_request",
                        reason=proposal["reason"],
                        idempotency_key=proposal["idempotency_key"],
                    )
                    approval_session.add(approval)
                    await approval_session.commit()
                    await approval_session.refresh(approval)
                yield serialize_sse("approval_required", {"approval_id": approval.id, **proposal})
                yield serialize_sse("done", {"status": "waiting_approval"})
                return
            answer = result.get("answer", "暂时无法回答。")
            if result.get("model_used"):
                yield serialize_sse(
                    "model_finished",
                    {
                        "provider": result.get("model_provider"),
                        "model": result.get("model_name"),
                    },
                )
            async with request.app.state.session_factory() as message_session:
                message_session.add(
                    Message(
                        conversation_id=conversation_id,
                        role="assistant",
                        content=answer,
                        references=result.get("references", []),
                    )
                )
                await message_session.commit()
            # 当前是 UI 文本分块，不是模型原生 Token 流；真实节点流可改用 astream_events。
            for index in range(0, len(answer), 18):
                yield serialize_sse("message_delta", {"content": answer[index : index + 18]})
            yield serialize_sse("done", {"status": "completed"})
        except Exception as exc:
            yield serialize_sse("error", {"message": str(exc)})

    return StreamingResponse(events(), media_type="text/event-stream")


@router.get("/approvals")
async def list_approvals(
    _: dict = Depends(require_agent), session: AsyncSession = Depends(get_session)
) -> list[dict]:
    items = (await session.scalars(select(Approval).order_by(Approval.created_at.desc()))).all()
    return [
        {
            "id": item.id,
            "conversation_id": item.conversation_id,
            "customer_id": item.customer_id,
            "order_id": item.order_id,
            "action": item.action,
            "reason": item.reason,
            "status": item.status,
            "created_at": item.created_at.isoformat(),
        }
        for item in items
    ]


@router.post("/conversations/{conversation_id}/human-replies")
async def create_human_reply(
    conversation_id: str,
    payload: HumanReplyRequest,
    identity: dict = Depends(require_agent),
    session: AsyncSession = Depends(get_session),
) -> dict:
    conversation = await _owned_conversation(session, conversation_id, identity)
    message = await create_human_message(session, conversation, payload.content)
    return {"id": message.id, "role": message.role, "content": message.content,
            "references": message.references, "created_at": message.created_at.isoformat(),
            "conversation_escalated": True}


@router.post("/approvals/{approval_id}/decision")
async def decide_approval(
    approval_id: str,
    payload: ApprovalDecision,
    request: Request,
    _: dict = Depends(require_agent),
    session: AsyncSession = Depends(get_session),
) -> dict:
    # 先持久化客服决定，再用同一 thread_id 恢复原工作流。
    approval = await session.get(Approval, approval_id)
    if not approval:
        raise HTTPException(status_code=404, detail="Approval not found")
    if approval.status != "pending":
        raise HTTPException(status_code=409, detail="Approval already decided")
    approval.status = "approved" if payload.decision == "approve" else "rejected"
    approval.decided_at = datetime.now(UTC)
    await session.commit()
    result = await request.app.state.agent_graph.ainvoke(
        Command(resume={"decision": payload.decision, "note": payload.note}),
        config={"configurable": {"thread_id": approval.conversation_id}},
    )
    answer = result.get("answer", "审批已处理。")
    session.add(Message(conversation_id=approval.conversation_id, role="assistant", content=answer))
    await session.commit()
    return {"approval_id": approval.id, "status": approval.status, "answer": answer}


@router.get("/metrics/summary")
async def metrics_summary(
    _: dict = Depends(require_agent), session: AsyncSession = Depends(get_session)
) -> dict:
    conversations = await session.scalar(select(func.count(Conversation.id))) or 0
    escalated = await session.scalar(
        select(func.count(Conversation.id)).where(Conversation.escalated.is_(True))
    ) or 0
    # 看板工具指标排除模型生成轨迹，避免 LLM 延迟扭曲业务工具耗时。
    business_trace = ToolTrace.tool_name.not_like("llm\\_%", escape="\\")
    traces = await session.scalar(select(func.count(ToolTrace.id)).where(business_trace)) or 0
    successful = await session.scalar(
        select(func.count(ToolTrace.id)).where(business_trace, ToolTrace.success.is_(True))
    ) or 0
    average_ms = await session.scalar(
        select(func.avg(ToolTrace.duration_ms)).where(business_trace)
    ) or 0
    return {
        "conversations": conversations,
        "resolution_rate": round((conversations - escalated) / conversations, 3) if conversations else 0,
        "escalation_rate": round(escalated / conversations, 3) if conversations else 0,
        "tool_success_rate": round(successful / traces, 3) if traces else 0,
        "average_tool_latency_ms": round(float(average_ms), 1),
    }
