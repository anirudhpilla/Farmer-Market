from datetime import UTC, datetime, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock

from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

import app.api.orders as orders_api
from app.config import get_settings
from app.database import get_db_session
from app.main import app
from app.models import (
    Cart,
    CartItem,
    CartState,
    GuestSession,
    Order,
    OrderItem,
    OrderStatus,
    Product,
    ProductStatus,
)
from app.schemas import CheckoutItem, CheckoutRequest
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
    return Cart(id=10, guest_session_id=5, state=CartState.OPEN, version=3)


def product() -> Product:
    return Product(
        id=7,
        name="Tomatoes — 1 kg pack",
        category_id=3,
        farmer_name="Sunrise Organic Farm",
        description="Ripe tomatoes selected for curries and salads.",
        price=Decimal("75.00"),
        available_quantity=8,
        image_url="https://example.com/tomatoes.jpg",
        status=ProductStatus.ACTIVE,
        is_deleted=False,
        version=1,
    )


def completed_order(fingerprint: str) -> Order:
    return Order(
        id=22,
        cart_id=10,
        guest_session_id=5,
        status=OrderStatus.CONFIRMED,
        currency="INR",
        grand_total=Decimal("150.00"),
        idempotency_key="checkout-key-1",
        request_fingerprint=fingerprint,
        created_at=datetime.now(UTC),
        items=[
            OrderItem(
                id=30,
                product_id=7,
                product_name_snapshot="Tomatoes — 1 kg pack",
                unit_price_snapshot=Decimal("75.00"),
                quantity=2,
            )
        ],
    )


def checkout_body(price: str = "75.00") -> dict:
    return {
        "expected_cart_version": 3,
        "items": [{"product_id": 7, "quantity": 2, "unit_price": price}],
    }


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


async def test_checkout_decrements_stock_and_snapshots_order(monkeypatch) -> None:
    session = AsyncMock(spec=AsyncSession)
    cart = open_cart()
    current_product = product()
    cart_item = CartItem(id=4, cart_id=10, product_id=7, quantity=2)
    monkeypatch.setattr(orders_api, "find_guest", AsyncMock(return_value=guest_session()))
    monkeypatch.setattr(orders_api, "find_open_cart", AsyncMock(return_value=cart))
    session.scalar.return_value = None
    session.scalars.side_effect = [[cart_item], [current_product]]

    async def assign_database_values() -> None:
        order = session.add.call_args.args[0]
        order.id = 22
        order.created_at = datetime.now(UTC)
        for item_id, item in enumerate(order.items, start=30):
            item.id = item_id

    session.flush.side_effect = assign_database_values
    response = await request_with_session(
        session,
        "POST",
        "/api/v1/orders/checkout",
        headers={
            "Origin": ORIGIN,
            "X-Guest-CSRF-Token": CSRF,
            "Idempotency-Key": "checkout-key-1",
        },
        json=checkout_body(),
    )

    assert response.status_code == 201
    assert response.json()["grand_total"] == "150.00"
    assert response.json()["items"][0]["product_name"] == current_product.name
    assert current_product.available_quantity == 6
    assert current_product.version == 2
    assert cart.state == CartState.CONVERTED
    session.commit.assert_awaited_once()


async def test_checkout_rejects_price_change_without_decrement(monkeypatch) -> None:
    session = AsyncMock(spec=AsyncSession)
    current_product = product()
    monkeypatch.setattr(orders_api, "find_guest", AsyncMock(return_value=guest_session()))
    monkeypatch.setattr(orders_api, "find_open_cart", AsyncMock(return_value=open_cart()))
    session.scalar.return_value = None
    session.scalars.side_effect = [
        [CartItem(id=4, cart_id=10, product_id=7, quantity=2)],
        [current_product],
    ]

    response = await request_with_session(
        session,
        "POST",
        "/api/v1/orders/checkout",
        headers={
            "Origin": ORIGIN,
            "X-Guest-CSRF-Token": CSRF,
            "Idempotency-Key": "checkout-key-1",
        },
        json=checkout_body(price="70.00"),
    )

    assert response.status_code == 409
    assert "price" in response.json()["detail"]
    assert current_product.available_quantity == 8
    session.commit.assert_not_awaited()


async def test_successful_retry_returns_original_order(monkeypatch) -> None:
    session = AsyncMock(spec=AsyncSession)
    body = CheckoutRequest(
        expected_cart_version=3,
        items=[CheckoutItem(product_id=7, quantity=2, unit_price=Decimal("75.00"))],
    )
    original = completed_order(orders_api.checkout_fingerprint(body))
    monkeypatch.setattr(orders_api, "find_guest", AsyncMock(return_value=guest_session()))
    session.scalar.return_value = original

    response = await request_with_session(
        session,
        "POST",
        "/api/v1/orders/checkout",
        headers={
            "Origin": ORIGIN,
            "X-Guest-CSRF-Token": CSRF,
            "Idempotency-Key": "checkout-key-1",
        },
        json=checkout_body(),
    )

    assert response.status_code == 200
    assert response.json()["id"] == 22
    assert response.json()["items"][0]["unit_price"] == "75.00"
    session.commit.assert_not_awaited()


async def test_reused_key_cannot_change_the_request(monkeypatch) -> None:
    session = AsyncMock(spec=AsyncSession)
    monkeypatch.setattr(orders_api, "find_guest", AsyncMock(return_value=guest_session()))
    session.scalar.return_value = completed_order("different-fingerprint")

    response = await request_with_session(
        session,
        "POST",
        "/api/v1/orders/checkout",
        headers={
            "Origin": ORIGIN,
            "X-Guest-CSRF-Token": CSRF,
            "Idempotency-Key": "checkout-key-1",
        },
        json=checkout_body(),
    )

    assert response.status_code == 409
    session.commit.assert_not_awaited()


def test_checkout_fingerprint_does_not_depend_on_item_order() -> None:
    first = CheckoutRequest(
        expected_cart_version=4,
        items=[
            CheckoutItem(product_id=2, quantity=1, unit_price=Decimal("20.00")),
            CheckoutItem(product_id=1, quantity=3, unit_price=Decimal("10.00")),
        ],
    )
    second = CheckoutRequest(
        expected_cart_version=4,
        items=list(reversed(first.items)),
    )

    assert orders_api.checkout_fingerprint(first) == orders_api.checkout_fingerprint(second)


async def test_guest_order_query_is_scoped_to_owner(monkeypatch) -> None:
    session = AsyncMock(spec=AsyncSession)
    monkeypatch.setattr(orders_api, "find_guest", AsyncMock(return_value=guest_session()))
    session.scalar.return_value = None

    response = await request_with_session(session, "GET", "/api/v1/orders/99")

    assert response.status_code == 404
    query = session.scalar.await_args.args[0]
    assert "orders.guest_session_id" in str(query)


async def test_admin_orders_rejects_anonymous_request() -> None:
    session = AsyncMock(spec=AsyncSession)

    response = await request_with_session(session, "GET", "/api/v1/admin/orders")

    assert response.status_code == 401


async def test_guest_order_list_scopes_count_and_rows_and_paginates(monkeypatch) -> None:
    guest = guest_session()
    monkeypatch.setattr(orders_api, "find_guest", AsyncMock(return_value=guest))
    session = AsyncMock(spec=AsyncSession)
    session.scalar.return_value = 21
    session.scalars.return_value = [completed_order("fingerprint")]

    response = await request_with_session(
        session, "GET", "/api/v1/orders?page=2&page_size=20"
    )

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 21
    assert body["total_pages"] == 2
    assert body["page"] == 2
    assert body["items"][0]["grand_total"] == "150.00"
    for query in (session.scalar.await_args.args[0], session.scalars.await_args.args[0]):
        assert str(query.whereclause) == "orders.guest_session_id = :guest_session_id_1"
        assert query.compile().params["guest_session_id_1"] == guest.id
    query = session.scalars.await_args.args[0]
    assert query._offset_clause.value == 20
    assert query._limit_clause.value == 20
    assert "orders.created_at DESC, orders.id DESC" in str(query)


async def test_guest_order_list_empty(monkeypatch) -> None:
    monkeypatch.setattr(orders_api, "find_guest", AsyncMock(return_value=guest_session()))
    session = AsyncMock(spec=AsyncSession)
    session.scalar.return_value = 0
    session.scalars.return_value = []
    response = await request_with_session(session, "GET", "/api/v1/orders")
    assert response.status_code == 200
    assert response.json()["items"] == []
    assert response.json()["total_pages"] == 0


async def test_guest_order_list_rejects_expired_session() -> None:
    session = AsyncMock(spec=AsyncSession)
    guest = guest_session()
    guest.expires_at = datetime.now(UTC) - timedelta(seconds=1)
    session.scalar.return_value = guest
    response = await request_with_session(session, "GET", "/api/v1/orders")
    assert response.status_code == 401
    session.scalars.assert_not_awaited()


async def test_guest_order_list_rejects_missing_cookie() -> None:
    session = AsyncMock(spec=AsyncSession)

    async def override_session():
        yield session

    app.dependency_overrides[get_db_session] = override_session
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/v1/orders")
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 401
    session.scalar.assert_not_awaited()


async def test_guest_order_list_validates_pagination() -> None:
    session = AsyncMock(spec=AsyncSession)
    for query in ("page=0", "page_size=51"):
        response = await request_with_session(session, "GET", f"/api/v1/orders?{query}")
        assert response.status_code == 422
    session.scalar.assert_not_awaited()
