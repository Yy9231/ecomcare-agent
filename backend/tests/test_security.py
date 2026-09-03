import pytest
from fastapi import HTTPException

from app.security import create_token, current_identity, hash_password, verify_password


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
