import uuid
from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def new_id() -> str:
    return str(uuid.uuid4())


class Customer(Base):
    __tablename__ = "customers"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    name: Mapped[str] = mapped_column(String(80))
    tier: Mapped[str] = mapped_column(String(20), default="standard")


class Account(Base):
    __tablename__ = "accounts"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    username: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(256))
    role: Mapped[str] = mapped_column(String(20))
    customer_id: Mapped[str] = mapped_column(ForeignKey("customers.id"), index=True)
    model_provider: Mapped[str | None] = mapped_column(String(40), nullable=True)
    model_name: Mapped[str | None] = mapped_column(String(160), nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class AccountModelConfig(Base):
    """保存某个账号在单个供应商下的模型参数与加密凭据。"""
    __tablename__ = "account_model_configs"
    __table_args__ = (UniqueConstraint("account_id", "provider"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    account_id: Mapped[str] = mapped_column(ForeignKey("accounts.id"), index=True)
    provider: Mapped[str] = mapped_column(String(40))
    model_name: Mapped[str] = mapped_column(String(160))
    base_url: Mapped[str] = mapped_column(String(500), default="")
    api_key_encrypted: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class Product(Base):
    __tablename__ = "products"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    sku: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(120))
    category: Mapped[str] = mapped_column(String(40))
    price: Mapped[float] = mapped_column(Float)
    warranty_months: Mapped[int] = mapped_column(Integer, default=12)


class Order(Base):
    __tablename__ = "orders"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    order_no: Mapped[str] = mapped_column(String(30), unique=True, index=True)
    customer_id: Mapped[str] = mapped_column(ForeignKey("customers.id"), index=True)
    product_id: Mapped[str] = mapped_column(ForeignKey("products.id"))
    status: Mapped[str] = mapped_column(String(30))
    amount: Mapped[float] = mapped_column(Float)
    purchased_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    tracking_no: Mapped[str | None] = mapped_column(String(50))
    carrier: Mapped[str | None] = mapped_column(String(40))
    estimated_delivery: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    product: Mapped[Product] = relationship()


class KnowledgeChunk(Base):
    """RAG 文档片段；正文、来源、版本和向量共同保证回答可追溯。"""
    __tablename__ = "knowledge_chunks"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    title: Mapped[str] = mapped_column(String(160))
    source: Mapped[str] = mapped_column(String(160))
    category: Mapped[str] = mapped_column(String(40))
    version: Mapped[str] = mapped_column(String(20), default="1.0")
    content: Mapped[str] = mapped_column(Text)
    embedding: Mapped[list[float]] = mapped_column(Vector(1536))


class Conversation(Base):
    """客户会话及人工接管、客服已读位置等服务状态。"""
    __tablename__ = "conversations"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    customer_id: Mapped[str] = mapped_column(ForeignKey("customers.id"), index=True)
    status: Mapped[str] = mapped_column(String(20), default="open")
    escalated: Mapped[bool] = mapped_column(Boolean, default=False)
    agent_last_read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Message(Base):
    __tablename__ = "messages"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    conversation_id: Mapped[str] = mapped_column(ForeignKey("conversations.id"), index=True)
    role: Mapped[str] = mapped_column(String(20))
    content: Mapped[str] = mapped_column(Text)
    references: Mapped[list] = mapped_column(JSONB, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ToolTrace(Base):
    """记录工具和模型调用结果、成功状态与耗时，用于审计和指标。"""
    __tablename__ = "tool_traces"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    conversation_id: Mapped[str] = mapped_column(ForeignKey("conversations.id"), index=True)
    tool_name: Mapped[str] = mapped_column(String(80))
    success: Mapped[bool] = mapped_column(Boolean)
    input_data: Mapped[dict] = mapped_column(JSONB, default=dict)
    output_data: Mapped[dict] = mapped_column(JSONB, default=dict)
    duration_ms: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Approval(Base):
    """LangGraph 中断对应的人工审批记录，幂等键阻止重复提案。"""
    __tablename__ = "approvals"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    conversation_id: Mapped[str] = mapped_column(ForeignKey("conversations.id"), index=True)
    customer_id: Mapped[str] = mapped_column(ForeignKey("customers.id"))
    order_id: Mapped[str] = mapped_column(ForeignKey("orders.id"))
    action: Mapped[str] = mapped_column(String(50))
    reason: Mapped[str] = mapped_column(Text)
    idempotency_key: Mapped[str] = mapped_column(String(80), unique=True)
    status: Mapped[str] = mapped_column(String(20), default="pending")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class AfterSalesRequest(Base):
    """审批通过后形成的最终售后业务记录。"""
    __tablename__ = "after_sales_requests"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    order_id: Mapped[str] = mapped_column(ForeignKey("orders.id"))
    customer_id: Mapped[str] = mapped_column(ForeignKey("customers.id"))
    reason: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), default="created")
    idempotency_key: Mapped[str] = mapped_column(String(80), unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
