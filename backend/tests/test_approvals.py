from unittest.mock import AsyncMock, Mock

import pytest

from app.models import Approval
from app.services.approvals import ApprovalConflictError, decide_pending_approval


def pending_approval() -> Approval:
    return Approval(
        id="approval-1",
        conversation_id="conversation-1",
        customer_id="customer-1",
        order_id="order-1",
        action="create_after_sales_request",
        reason="商品不合适",
        idempotency_key="conversation-1:message-1",
        status="pending",
    )


@pytest.mark.asyncio
async def test_approval_stays_pending_when_graph_resume_fails() -> None:
    approval = pending_approval()
    session = AsyncMock()
    session.scalar.return_value = approval
    graph = Mock()
    graph.ainvoke = AsyncMock(side_effect=RuntimeError("checkpoint unavailable"))

    with pytest.raises(ApprovalConflictError, match="审批执行失败") as raised:
        await decide_pending_approval(session, graph, approval.id, "approve", "通过")

    assert raised.value.status_code == 503
    assert approval.status == "pending"
    session.rollback.assert_awaited_once()
    session.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_approval_commits_decision_and_customer_message_after_resume() -> None:
    approval = pending_approval()
    session = AsyncMock()
    session.scalar.return_value = approval
    session.add = Mock()
    graph = Mock()
    graph.ainvoke = AsyncMock(return_value={"answer": "售后申请已创建，申请编号：AS-1。"})

    result = await decide_pending_approval(session, graph, approval.id, "approve", "通过")

    assert result["status"] == "approved"
    assert approval.status == "approved"
    assert session.add.call_args.args[0].content == "售后申请已创建，申请编号：AS-1。"
    session.commit.assert_awaited_once()
