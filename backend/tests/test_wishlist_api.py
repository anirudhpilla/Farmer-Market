from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock

from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from test_admin_products_api import sample_product

import app.api.wishlist as wishlist_api
from app.config import get_settings
from app.database import get_db_session
from app.main import app
from app.models import GuestSession, ProductStatus, WishlistItem
from app.security import digest_token

ORIGIN = get_settings().frontend_origin
CSRF = "wishlist-csrf"


def guest_session() -> GuestSession:
    return GuestSession(
        id=5,
        token_digest=digest_token("guest-token"),
        csrf_digest=digest_token(CSRF),
        expires_at=datetime.now(UTC) + timedelta(days=1),
    )


async def request_with_session(session: AsyncMock, method: str, path: str, **kwargs):
    async def override_session():
        yield session

    app.dependency_overrides[get_db_session] = override_session
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            client.cookies.set("guest_token", "guest-token")
            return await client.request(method, path, **kwargs)
    finally:
        app.dependency_overrides.clear()


async def test_get_wishlist_returns_only_guest_products(monkeypatch) -> None:
    session = AsyncMock(spec=AsyncSession)
    monkeypatch.setattr(wishlist_api, "find_guest", AsyncMock(return_value=guest_session()))
    session.scalars.return_value = [sample_product()]

    response = await request_with_session(session, "GET", "/api/v1/wishlist")

    assert response.status_code == 200
    assert response.json()["item_count"] == 1
    assert response.json()["items"][0]["id"] == 7
    query = session.scalars.call_args.args[0]
    assert "wishlist_items.guest_session_id" in str(query)


async def test_add_is_idempotent(monkeypatch) -> None:
    session = AsyncMock(spec=AsyncSession)
    product = sample_product()
    monkeypatch.setattr(wishlist_api, "find_guest", AsyncMock(return_value=guest_session()))
    session.get.return_value = product
    session.scalar.return_value = WishlistItem(id=3, guest_session_id=5, product_id=7)
    session.scalars.return_value = [product]

    response = await request_with_session(
        session,
        "POST",
        "/api/v1/wishlist/7",
        headers={"Origin": ORIGIN, "X-Guest-CSRF-Token": CSRF},
    )

    assert response.status_code == 200
    assert response.json()["item_count"] == 1
    session.add.assert_not_called()
    session.commit.assert_awaited_once()


async def test_add_rejects_inactive_product(monkeypatch) -> None:
    session = AsyncMock(spec=AsyncSession)
    product = sample_product()
    product.status = ProductStatus.INACTIVE
    monkeypatch.setattr(wishlist_api, "find_guest", AsyncMock(return_value=guest_session()))
    session.get.return_value = product

    response = await request_with_session(
        session,
        "POST",
        "/api/v1/wishlist/7",
        headers={"Origin": ORIGIN, "X-Guest-CSRF-Token": CSRF},
    )

    assert response.status_code == 404
    session.commit.assert_not_awaited()


async def test_mutation_requires_csrf(monkeypatch) -> None:
    session = AsyncMock(spec=AsyncSession)
    monkeypatch.setattr(wishlist_api, "find_guest", AsyncMock(return_value=guest_session()))

    response = await request_with_session(
        session,
        "POST",
        "/api/v1/wishlist/7",
        headers={"Origin": ORIGIN},
    )

    assert response.status_code == 403
    session.get.assert_not_awaited()


async def test_remove_is_scoped_to_guest(monkeypatch) -> None:
    session = AsyncMock(spec=AsyncSession)
    monkeypatch.setattr(wishlist_api, "find_guest", AsyncMock(return_value=guest_session()))
    session.scalars.return_value = []

    response = await request_with_session(
        session,
        "DELETE",
        "/api/v1/wishlist/7",
        headers={"Origin": ORIGIN, "X-Guest-CSRF-Token": CSRF},
    )

    assert response.status_code == 200
    assert response.json() == {"items": [], "item_count": 0}
    statement = session.execute.call_args.args[0]
    assert "wishlist_items.guest_session_id" in str(statement)
    assert "wishlist_items.product_id" in str(statement)
    session.commit.assert_awaited_once()
