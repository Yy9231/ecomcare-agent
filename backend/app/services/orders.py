from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import AfterSalesRequest, Order


async def get_owned_order(session: AsyncSession, customer_id: str, order_no: str) -> Order | None:
    """同时按订单号和可信客户身份过滤，形成订单资源级授权边界。"""
    statement = (
        select(Order)
        .options(selectinload(Order.product))
        .where(Order.order_no == order_no, Order.customer_id == customer_id)
    )
    return await session.scalar(statement)


def order_payload(order: Order) -> dict:
    return {
        "order_id": order.id,
        "order_no": order.order_no,
        "product": order.product.name,
        "status": order.status,
        "amount": order.amount,
        "purchased_at": order.purchased_at.isoformat(),
    }


def logistics_payload(order: Order) -> dict:
    return {
        **order_payload(order),
        "carrier": order.carrier,
        "tracking_no": order.tracking_no,
        "estimated_delivery": (
            order.estimated_delivery.isoformat() if order.estimated_delivery else None
        ),
    }


def return_eligibility(order: Order, now: datetime | None = None) -> dict:
    """使用确定性七天规则判断资格，避免让概率模型决定业务政策。"""
    current = now or datetime.now(UTC)
    if order.status != "delivered" or not order.delivered_at:
        return {"eligible": False, "reason": "订单尚未签收，不能发起退货。"}
    delivered_at = order.delivered_at
    if delivered_at.tzinfo is None:
        delivered_at = delivered_at.replace(tzinfo=UTC)
    deadline = delivered_at + timedelta(days=7)
    eligible = current <= deadline
    return {
        "eligible": eligible,
        "reason": "仍在七天无理由退货期限内。" if eligible else "已超过七天无理由退货期限。",
        "deadline": deadline.isoformat(),
    }


async def create_after_sales(
    session: AsyncSession,
    order: Order,
    reason: str,
    idempotency_key: str,
) -> AfterSalesRequest:
    """审批通过后幂等创建售后单，重复恢复不会产生多条业务记录。"""
    existing = await session.scalar(
        select(AfterSalesRequest).where(
            AfterSalesRequest.idempotency_key == idempotency_key
        )
    )
    if existing:
        return existing
    request = AfterSalesRequest(
        order_id=order.id,
        customer_id=order.customer_id,
        reason=reason,
        idempotency_key=idempotency_key,
    )
    session.add(request)
    await session.commit()
    await session.refresh(request)
    return request
