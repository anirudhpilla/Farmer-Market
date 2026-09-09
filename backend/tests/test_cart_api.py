from datetime import UTC, datetime, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

import app.api.cart as cart_api
from app.config import get_settings
from app.database import get_db_session
from app.main import app
from app.models import Cart, CartItem, CartState, GuestSession, Product, ProductStatus
from app.security import digest_token

ORIGIN = get_settings().frontend_origin
CSRF = "guest-csrf"


def guest_session() -> GuestSession:
    return GuestSession(
        id=5,
        token_digest=digest_token("guest-token"),
        csrf_digest=digest_token(CSRF),
        expires_at=datetime.now(UTC) + timedelta(days=1),
    )


def open_cart() -> Cart:
    return Cart(id=10, guest_session_id=5, state=CartState.OPEN, version=2)


def product(stock: int = 8, status: ProductStatus = ProductStatus.ACTIVE) -> Product:
    return Product(
        id=7,
        name="Tomatoes — 1 kg pack",
        category_id=3,
        farmer_name="Sunrise Organic Farm",
        description="Ripe tomatoes selected for curries and salads.",
        price=Decimal("75.00"),
        available_quantity=stock,
        image_url="https://example.com/tomatoes.jpg",
        status=status,
        is_deleted=False,
        version=1,
    )


async def request_with_session(session: AsyncMock, method: str, path: str, **kwargs):
    cookies = kwargs.pop("cookies", {"guest_token": "guest-token"})

    async def override_session():
        yield session

    app.dependency_overrides[get_db_session] = override_session
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            client.cookies.update(cookies)
            return await client.request(method, path, **kwargs)
    finally:
        app.dependency_overrides.clear()


def result_with_rows(rows) -> MagicMock:
    result = MagicMock()
    result.all.return_value = rows
    return result


async def test_cart_totals_use_current_database_price() -> None:
    session = AsyncMock(spec=AsyncSession)
    cart = open_cart()
    item = CartItem(id=4, cart_id=10, product_id=7, quantity=3)
    session.execute.return_value = result_with_rows([(item, product())])

    response = await cart_api.read_cart(session, cart)

    assert response.item_count == 3
    assert response.items[0].line_total == Decimal("225.00")
    assert response.grand_total == Decimal("225.00")


async def test_cart_marks_quantity_that_now_exceeds_stock() -> None:
    session = AsyncMock(spec=AsyncSession)
    item = CartItem(id=4, cart_id=10, product_id=7, quantity=3)
    session.execute.return_value = result_with_rows([(item, product(stock=2))])

    response = await cart_api.read_cart(session, open_cart())

    assert response.items[0].issue == "insufficient_stock"


async def test_repeated_add_increments_existing_line(monkeypatch) -> None:
    session = AsyncMock(spec=AsyncSession)
    cart = open_cart()
    item = CartItem(id=4, cart_id=10, product_id=7, quantity=2)
    current_product = product()
    monkeypatch.setattr(cart_api, "find_guest", AsyncMock(return_value=guest_session()))
    session.get.return_value = current_product
    session.scalar.side_effect = [cart, item]
    session.execute.return_value = result_with_rows([(item, current_product)])

    response = await request_with_session(
        session,
        "POST",
        "/api/v1/cart/items",
        headers={"Origin": ORIGIN, "X-Guest-CSRF-Token": CSRF},
        json={"product_id": 7, "quantity": 3},
    )

    assert response.status_code == 200
    assert response.json()["items"][0]["quantity"] == 5
    assert cart.version == 3
    session.commit.assert_awaited_once()


async def test_add_rejects_quantity_above_stock(monkeypatch) -> None:
    session = AsyncMock(spec=AsyncSession)
    monkeypatch.setattr(cart_api, "find_guest", AsyncMock(return_value=guest_session()))
    session.get.return_value = product(stock=2)

    response = await request_with_session(
        session,
        "POST",
        "/api/v1/cart/items",
        headers={"Origin": ORIGIN, "X-Guest-CSRF-Token": CSRF},
        json={"product_id": 7, "quantity": 3},
    )

    assert response.status_code == 409
    session.commit.assert_not_awaited()


async def test_update_cannot_target_item_from_another_cart(monkeypatch) -> None:
    session = AsyncMock(spec=AsyncSession)
    monkeypatch.setattr(cart_api, "find_guest", AsyncMock(return_value=guest_session()))
    session.scalar.side_effect = [open_cart(), None]

    response = await request_with_session(
        session,
        "PATCH",
        "/api/v1/cart/items/999",
        headers={"Origin": ORIGIN, "X-Guest-CSRF-Token": CSRF},
        json={"quantity": 2},
    )

    assert response.status_code == 404
    item_query = session.scalar.await_args_list[1].args[0]
    assert "cart_items.cart_id" in str(item_query)
    session.commit.assert_not_awaited()


async def test_mutation_rejects_wrong_csrf_before_cart_change(monkeypatch) -> None:
    session = AsyncMock(spec=AsyncSession)
    monkeypatch.setattr(cart_api, "find_guest", AsyncMock(return_value=guest_session()))

    response = await request_with_session(
        session,
        "DELETE",
        "/api/v1/cart/items/4",
        headers={"Origin": ORIGIN, "X-Guest-CSRF-Token": "wrong"},
    )

    assert response.status_code == 403
    session.scalar.assert_not_awaited()
    session.commit.assert_not_awaited()
