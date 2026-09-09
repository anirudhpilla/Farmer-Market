from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock

from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import get_db_session
from app.main import app
from app.models import RefreshSession, RefreshToken, User, UserRole
from app.security import create_access_token, digest_token, hash_password

ORIGIN = get_settings().frontend_origin


def admin_user() -> User:
    return User(
        id=4,
        email="admin@example.com",
        password_hash=hash_password("a-secure-password"),
        role=UserRole.ADMIN,
    )


async def request_with_session(session: AsyncMock, method: str, path: str, **kwargs):
    cookies = kwargs.pop("cookies", None)

    async def override_session():
        yield session

    app.dependency_overrides[get_db_session] = override_session
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            if cookies:
                client.cookies.update(cookies)
            return await client.request(method, path, **kwargs)
    finally:
        app.dependency_overrides.clear()


async def test_login_creates_refresh_family_and_sets_two_cookies() -> None:
    session = AsyncMock(spec=AsyncSession)
    session.scalar.return_value = admin_user()

    response = await request_with_session(
        session,
        "POST",
        "/api/v1/auth/login",
        headers={"Origin": ORIGIN},
        json={"email": "ADMIN@example.com", "password": "a-secure-password"},
    )

    assert response.status_code == 200
    assert response.json()["user"]["email"] == "admin@example.com"
    assert response.cookies["refresh_token"]
    assert response.cookies["csrf_token"]
    assert "HttpOnly" in response.headers["set-cookie"]
    session.commit.assert_awaited_once()


async def test_refresh_consumes_old_token_and_creates_replacement() -> None:
    now = datetime.now(UTC)
    old_token = "old-refresh-secret"
    csrf_token = "csrf-secret"
    stored_token = RefreshToken(
        id=8,
        session_id=3,
        token_digest=digest_token(old_token),
        expires_at=now + timedelta(days=1),
    )
    family = RefreshSession(
        id=3,
        user_id=4,
        csrf_digest=digest_token(csrf_token),
        absolute_expires_at=now + timedelta(days=1),
    )
    session = AsyncMock(spec=AsyncSession)
    session.scalar.return_value = stored_token
    session.get.side_effect = [family, admin_user()]

    response = await request_with_session(
        session,
        "POST",
        "/api/v1/auth/refresh",
        headers={"Origin": ORIGIN, "X-CSRF-Token": csrf_token},
        cookies={"refresh_token": old_token},
    )

    assert response.status_code == 200
    assert response.cookies["refresh_token"] != old_token
    assert stored_token.consumed_at is not None
    session.add.assert_called_once()
    session.commit.assert_awaited_once()


async def test_reusing_consumed_refresh_token_revokes_family() -> None:
    now = datetime.now(UTC)
    old_token = "already-used-token"
    csrf_token = "csrf-secret"
    stored_token = RefreshToken(
        id=8,
        session_id=3,
        token_digest=digest_token(old_token),
        expires_at=now + timedelta(days=1),
        consumed_at=now - timedelta(seconds=1),
    )
    family = RefreshSession(
        id=3,
        user_id=4,
        csrf_digest=digest_token(csrf_token),
        absolute_expires_at=now + timedelta(days=1),
    )
    session = AsyncMock(spec=AsyncSession)
    session.scalar.return_value = stored_token
    session.get.return_value = family

    response = await request_with_session(
        session,
        "POST",
        "/api/v1/auth/refresh",
        headers={"Origin": ORIGIN, "X-CSRF-Token": csrf_token},
        cookies={"refresh_token": old_token},
    )

    assert response.status_code == 401
    assert "reuse detected" in response.json()["detail"]
    assert family.revoked_at is not None
    session.commit.assert_awaited_once()


async def test_wrong_csrf_cannot_trigger_replay_revocation() -> None:
    now = datetime.now(UTC)
    stored_token = RefreshToken(
        id=8,
        session_id=3,
        token_digest=digest_token("already-used-token"),
        expires_at=now + timedelta(days=1),
        consumed_at=now - timedelta(seconds=1),
    )
    family = RefreshSession(
        id=3,
        user_id=4,
        csrf_digest=digest_token("correct-csrf"),
        absolute_expires_at=now + timedelta(days=1),
    )
    session = AsyncMock(spec=AsyncSession)
    session.scalar.return_value = stored_token
    session.get.return_value = family

    response = await request_with_session(
        session,
        "POST",
        "/api/v1/auth/refresh",
        headers={"Origin": ORIGIN, "X-CSRF-Token": "wrong-csrf"},
        cookies={"refresh_token": "already-used-token"},
    )

    assert response.status_code == 403
    assert family.revoked_at is None
    session.commit.assert_not_awaited()


async def test_me_requires_and_validates_access_token() -> None:
    user = admin_user()
    session = AsyncMock(spec=AsyncSession)
    session.get.return_value = user

    response = await request_with_session(
        session,
        "GET",
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {create_access_token(user)}"},
    )

    assert response.status_code == 200
    assert response.json() == {"id": 4, "email": "admin@example.com", "role": "admin"}


async def test_cookie_mutations_reject_untrusted_origins() -> None:
    session = AsyncMock(spec=AsyncSession)

    response = await request_with_session(
        session,
        "POST",
        "/api/v1/auth/refresh",
        headers={"Origin": "https://attacker.example"},
    )

    assert response.status_code == 403
    session.scalar.assert_not_awaited()
