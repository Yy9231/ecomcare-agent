from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Conversation, Customer, Message


async def list_conversation_summaries(session: AsyncSession, identity: dict) -> list[dict]:
    """聚合最近活动、消息数和服务端未读数，供客户与客服列表复用。"""
    message_count = (
        select(func.count(Message.id))
        .where(Message.conversation_id == Conversation.id)
        .correlate(Conversation)
        .scalar_subquery()
    )
    latest_message_at = (
        select(func.max(Message.created_at))
        .where(Message.conversation_id == Conversation.id)
        .correlate(Conversation)
        .scalar_subquery()
    )
    unread_count = (
        select(func.count(Message.id))
        .where(
            Message.conversation_id == Conversation.id,
            Message.role == "user",
            (Conversation.agent_last_read_at.is_(None))
            | (Message.created_at > Conversation.agent_last_read_at),
        )
        .correlate(Conversation)
        .scalar_subquery()
    )
    # 有消息按最后消息排序；空会话回退到创建时间，确保新消息会话自动置顶。
    activity = func.coalesce(latest_message_at, Conversation.created_at)
    statement = select(
        Conversation,
        Customer.name.label("customer_name"),
        message_count.label("message_count"),
        activity.label("latest_activity_at"),
        unread_count.label("unread_count"),
    ).join(Customer, Customer.id == Conversation.customer_id).order_by(activity.desc()).limit(50)
    if identity["role"] != "agent":
        statement = statement.where(Conversation.customer_id == identity["customer_id"])
    rows = (await session.execute(statement)).all()
    return [
        {
            "id": item.id,
            "customer_id": item.customer_id,
            "customer_name": customer_name,
            "status": item.status,
            "escalated": item.escalated,
            "created_at": item.created_at.isoformat(),
            "latest_activity_at": latest_activity.isoformat(),
            "message_count": count,
            "unread_count": unread if identity["role"] == "agent" else 0,
        }
        for item, customer_name, count, latest_activity, unread in rows
    ]


async def mark_agent_read(session: AsyncSession, conversation: Conversation) -> datetime:
    # 记录“打开时已存在的最新客户消息”，避免并发到达的新消息被误标为已读。
    latest_user_at = await session.scalar(
        select(func.max(Message.created_at)).where(
            Message.conversation_id == conversation.id, Message.role == "user"
        )
    )
    conversation.agent_last_read_at = latest_user_at or datetime.now(UTC)
    await session.commit()
    return conversation.agent_last_read_at


async def create_human_message(
    session: AsyncSession,
    conversation: Conversation,
    content: str,
) -> Message:
    """持久化人工消息，并允许客服发送第一条消息时主动接管会话。"""
    conversation.escalated = True
    message = Message(conversation_id=conversation.id, role="human", content=content)
    session.add(message)
    await session.commit()
    await session.refresh(message)
    return message
