from datetime import UTC, datetime

from langgraph.types import Command
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Approval, Message


class ApprovalConflictError(Exception):
    """将审批领域冲突转换为稳定的 HTTP 状态和中文提示。"""

    def __init__(self, status_code: int, detail: str) -> None:
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


async def decide_pending_approval(
    session: AsyncSession,
    graph,
    approval_id: str,
    decision: str,
    note: str,
) -> dict:
    """锁定待审批记录，成功恢复 Agent 后再原子保存决定和客户消息。"""
    approval = await session.scalar(
        select(Approval)
        .where(Approval.id == approval_id, Approval.status == "pending")
        .with_for_update()
    )
    if not approval:
        existing = await session.get(Approval, approval_id)
        if not existing:
            raise ApprovalConflictError(404, "Approval not found")
        raise ApprovalConflictError(409, "Approval already decided")

    try:
        result = await graph.ainvoke(
            Command(resume={"decision": decision, "note": note}),
            config={"configurable": {"thread_id": approval.conversation_id}},
        )
        answer = result.get("answer", "审批已处理。")
        approval.status = "approved" if decision == "approve" else "rejected"
        approval.decided_at = datetime.now(UTC)
        session.add(
            Message(conversation_id=approval.conversation_id, role="assistant", content=answer)
        )
        await session.commit()
    except Exception as exc:
        # 恢复失败时撤销行锁事务，审批仍为 pending，客服可以安全重试。
        await session.rollback()
        raise ApprovalConflictError(503, "审批执行失败，当前申请仍为待审批，请重试") from exc
    return {"approval_id": approval.id, "status": approval.status, "answer": answer}
