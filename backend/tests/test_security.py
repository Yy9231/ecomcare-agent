from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException

from app.models import Account
from app.security import (
    active_identity,
    create_token,
    current_identity,
    hash_password,
    verify_password,
)


def test_password_hash_round_trip() -> None:
    encoded = hash_password("customer123")
    assert encoded != "customer123"
    assert verify_password("customer123", encoded) is True


def test_wrong_password_is_rejected() -> None:
    encoded = hash_password("customer123")
    assert verify_password("wrong-password", encoded) is False
    assert verify_password("customer123", "invalid-hash") is False


def test_custom_header_token_is_accepted() -> None:
    token = create_token("ACC-001", "CUST-001", "customer")

    identity = current_identity(credentials=None, x_ecomcare_token=token)

    assert identity == {
        "account_id": "ACC-001",
        "customer_id": "CUST-001",
        "role": "customer",
    }


def test_missing_token_is_rejected() -> None:
    with pytest.raises(HTTPException) as exc_info:
        current_identity(credentials=None, x_ecomcare_token=None)

    assert exc_info.value.status_code == 401


@pytest.mark.asyncio
async def test_deactivated_account_is_rejected_even_with_valid_token_claims() -> None:
    session = AsyncMock()
    session.get.return_value = Account(
        id="ACC-001",
        username="customer1",
        password_hash="unused",
        role="customer",
        customer_id="CUST-001",
        active=False,
    )

    with pytest.raises(HTTPException) as raised:
        await active_identity(
            {"account_id": "ACC-001", "customer_id": "CUST-001", "role": "customer"},
            session,
        )

    assert raised.value.status_code == 401


@pytest.mark.asyncio
async def test_changed_account_binding_invalidates_old_token_claims() -> None:
    session = AsyncMock()
    session.get.return_value = Account(
        id="ACC-001",
        username="customer1",
        password_hash="unused",
        role="customer",
        customer_id="CUST-002",
        active=True,
    )

    with pytest.raises(HTTPException) as raised:
        await active_identity(
            {"account_id": "ACC-001", "customer_id": "CUST-001", "role": "customer"},
            session,
        )

    assert raised.value.status_code == 401
