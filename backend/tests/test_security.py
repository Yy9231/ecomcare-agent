from app.security import hash_password, verify_password


def test_password_hash_round_trip() -> None:
    encoded = hash_password("customer123")
    assert encoded != "customer123"
    assert verify_password("customer123", encoded) is True


def test_wrong_password_is_rejected() -> None:
    encoded = hash_password("customer123")
    assert verify_password("wrong-password", encoded) is False
    assert verify_password("customer123", "invalid-hash") is False
