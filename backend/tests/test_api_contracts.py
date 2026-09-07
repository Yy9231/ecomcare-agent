import pytest
from fastapi.routing import APIRoute
from pydantic import ValidationError

from app.api import router
from app.schemas import HumanReplyRequest, MessageRequest
from app.security import require_customer


def test_customer_stream_rejects_non_customer_role_at_dependency_boundary() -> None:
    route = next(
        item
        for item in router.routes
        if isinstance(item, APIRoute)
        and item.path == "/api/v1/conversations/{conversation_id}/messages/stream"
    )
    assert require_customer in {dependency.call for dependency in route.dependant.dependencies}


@pytest.mark.parametrize("schema", [MessageRequest, HumanReplyRequest])
def test_chat_messages_reject_whitespace_only_content(schema) -> None:
    with pytest.raises(ValidationError, match="消息内容不能为空"):
        schema(content=" \n\t ")


@pytest.mark.parametrize("schema", [MessageRequest, HumanReplyRequest])
def test_chat_messages_are_trimmed(schema) -> None:
    assert schema(content="  你好  ").content == "你好"
