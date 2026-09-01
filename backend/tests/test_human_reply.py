from unittest.mock import AsyncMock, Mock

import pytest

from app.models import Conversation
from app.services import conversations


@pytest.mark.asyncio
async def test_human_reply_takes_over_automatic_conversation() -> None:
    session = AsyncMock()
    session.add = Mock()
    conversation = Conversation(customer_id="customer-1", escalated=False)

    message = await conversations.create_human_message(
        session,
        conversation,
        "您好，我来协助处理。",
    )

    assert conversation.escalated is True
    assert message.role == "human"
    assert message.content == "您好，我来协助处理。"
    session.add.assert_called_once_with(message)
    session.commit.assert_awaited_once()
    session.refresh.assert_awaited_once_with(message)
