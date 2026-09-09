from fastapi import HTTPException

from app.api.auth import check_rate_limit, rate_attempts
from app.models import User, UserRole
from app.security import create_access_token, decode_access_token, hash_password, verify_password


def test_passwords_are_hashed_and_verified() -> None:
    stored_hash = hash_password("correct-horse-battery-staple")

    assert stored_hash != "correct-horse-battery-staple"
    assert verify_password("correct-horse-battery-staple", stored_hash)
    assert not verify_password("wrong-password", stored_hash)


def test_access_token_contains_the_expected_identity() -> None:
    user = User(id=12, email="admin@example.com", password_hash="unused", role=UserRole.ADMIN)

    claims = decode_access_token(create_access_token(user))

    assert claims["sub"] == "12"
    assert claims["role"] == "admin"
    assert claims["type"] == "access"


def test_process_local_auth_rate_limit() -> None:
    key = "test:rate-limit"
    rate_attempts.pop(key, None)
    check_rate_limit(key, limit=2)
    check_rate_limit(key, limit=2)

    try:
        check_rate_limit(key, limit=2)
    except HTTPException as error:
        assert error.status_code == 429
        assert error.headers == {"Retry-After": "60"}
    else:
        raise AssertionError("Expected the third request to be rate limited")
    finally:
        rate_attempts.pop(key, None)
