from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock

from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import get_db_session
from app.main import app
from app.models import GuestSession
from app.security import digest_token

ORIGIN = get_settings().frontend_origin


async def request_with_session(session: AsyncMock, **kwargs):
    cookies = kwargs.pop("cookies", None)

    async def override_session():
        yield session

    app.dependency_overrides[get_db_session] = override_session
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            if cookies:
                client.cookies.update(cookies)
            return await client.post("/api/v1/guest-session", **kwargs)
    finally:
        app.dependency_overrides.clear()


async def test_guest_bootstrap_creates_opaque_session_cookies() -> None:
    session = AsyncMock(spec=AsyncSession)
    session.scalar.return_value = None

    response = await request_with_session(session, headers={"Origin": ORIGIN})

    assert response.status_code == 204
    assert response.cookies["guest_token"]
    assert response.cookies["guest_csrf_token"]
    assert "HttpOnly" in response.headers["set-cookie"]
    session.add.assert_called_once()
    session.commit.assert_awaited_once()


async def test_guest_bootstrap_reissues_missing_csrf_value() -> None:
    raw_guest_token = "known-guest-token"
    guest = GuestSession(
        id=5,
        token_digest=digest_token(raw_guest_token),
        csrf_digest=digest_token("old-csrf"),
        expires_at=datetime.now(UTC) + timedelta(days=2),
    )
    session = AsyncMock(spec=AsyncSession)
    session.scalar.return_value = guest

    response = await request_with_session(
        session,
        headers={"Origin": ORIGIN},
        cookies={"guest_token": raw_guest_token},
    )

    assert response.status_code == 204
    assert response.cookies["guest_token"] == raw_guest_token
    assert response.cookies["guest_csrf_token"] != "old-csrf"
    assert guest.csrf_digest != digest_token("old-csrf")
    session.commit.assert_awaited_once()


async def test_guest_bootstrap_rejects_untrusted_origin() -> None:
    session = AsyncMock(spec=AsyncSession)

    response = await request_with_session(
        session,
        headers={"Origin": "https://attacker.example"},
    )

    assert response.status_code == 403
    session.scalar.assert_not_awaited()
