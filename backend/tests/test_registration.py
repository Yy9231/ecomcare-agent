from unittest.mock import AsyncMock, Mock

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from app import auth
from app.models import Account, Customer
from app.schemas import RegisterRequest


@pytest.mark.asyncio
async def test_register_creates_customer_account_and_session(monkeypatch) -> None:
    session = AsyncMock()
    session.add = Mock()
    session.scalar.return_value = None
    monkeypatch.setattr(auth, "hash_password", lambda password: f"hashed:{password}")

    response = await auth.register(
        RegisterRequest(username="new_user", display_name="新客户", password="secure123"),
        session,
    )

    customer = session.add.call_args_list[0].args[0]
    account = session.add.call_args_list[1].args[0]
    assert isinstance(customer, Customer)
    assert isinstance(account, Account)
    assert customer.name == "新客户"
    assert account.username == "new_user"
    assert account.password_hash == "hashed:secure123"
    assert account.role == "customer"
    assert account.customer_id == customer.id
    assert len(customer.id) <= 20
    assert len(account.id) <= 20
    assert response.role == "customer"
    assert response.display_name == "新客户"
    session.flush.assert_awaited_once()
    session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_register_rejects_duplicate_username() -> None:
    session = AsyncMock()
    session.scalar.return_value = Account(
        username="new_user",
        password_hash="unused",
        role="customer",
        customer_id="customer-1",
    )

    with pytest.raises(HTTPException) as raised:
        await auth.register(
            RegisterRequest(username="NEW_USER", display_name="另一位客户", password="secure123"),
            session,
        )

    assert raised.value.status_code == 409
    assert raised.value.detail == "该账号已被注册"
    session.commit.assert_not_awaited()


@pytest.mark.parametrize("username", ["ab", "含中文", "has space", "user@name"])
def test_register_rejects_invalid_username(username: str) -> None:
    with pytest.raises(ValidationError):
        RegisterRequest(username=username, display_name="测试客户", password="secure123")


def test_register_normalizes_username_and_display_name() -> None:
    payload = RegisterRequest(
        username="  New_User  ",
        display_name="  小杨  ",
        password="secure123",
    )
    assert payload.username == "new_user"
    assert payload.display_name == "小杨"
