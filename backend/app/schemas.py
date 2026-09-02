import re
from typing import Literal

from pydantic import BaseModel, Field, SecretStr, field_validator

USERNAME_PATTERN = re.compile(r"^[a-z0-9_]{3,32}$")


def _normalize_username(value: str) -> str:
    normalized = value.strip().lower()
    if not USERNAME_PATTERN.fullmatch(normalized):
        raise ValueError("账号只能包含 3–32 位英文字母、数字或下划线")
    return normalized


class LoginRequest(BaseModel):
    username: str = Field(min_length=3, max_length=80)
    password: str = Field(min_length=8, max_length=128)

    normalize_username = field_validator("username")(_normalize_username)


class RegisterRequest(BaseModel):
    username: str = Field(min_length=3, max_length=80)
    display_name: str = Field(min_length=2, max_length=40)
    password: str = Field(min_length=8, max_length=128)

    normalize_username = field_validator("username")(_normalize_username)

    @field_validator("display_name")
    @classmethod
    def normalize_display_name(cls, value: str) -> str:
        normalized = value.strip()
        if len(normalized) < 2:
            raise ValueError("昵称至少需要 2 个字符")
        return normalized


class LoginResponse(BaseModel):
    access_token: str
    username: str
    customer_id: str
    display_name: str
    role: Literal["customer", "agent"]


class ConversationCreate(BaseModel):
    pass


class MessageRequest(BaseModel):
    content: str = Field(min_length=1, max_length=2000)


class HumanReplyRequest(BaseModel):
    content: str = Field(min_length=1, max_length=2000)


class ModelPreferenceUpdate(BaseModel):
    provider: str = Field(min_length=2, max_length=40)
    model: str | None = Field(default=None, max_length=160)
    base_url: str = Field(default="", max_length=500)
    api_key: SecretStr = Field(default=SecretStr(""), max_length=4096)


class ApprovalDecision(BaseModel):
    decision: Literal["approve", "reject"]
    note: str = Field(default="", max_length=500)


class RouteDecision(BaseModel):
    intent: Literal[
        "order_query",
        "logistics_query",
        "knowledge_query",
        "return_check",
        "after_sales",
        "escalate",
        "general_chat",
    ]
    order_no: str | None = None
    reason: str | None = None
    confidence: float = Field(ge=0, le=1)
