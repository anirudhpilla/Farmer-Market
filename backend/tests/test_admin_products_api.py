from decimal import Decimal
from unittest.mock import AsyncMock

from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import get_current_admin
from app.database import get_db_session
from app.main import app
from app.models import Category, Product, ProductStatus, User, UserRole


def admin_user() -> User:
    return User(id=1, email="admin@example.com", password_hash="unused", role=UserRole.ADMIN)


def sample_product() -> Product:
    return Product(
        id=7,
        name="Tomatoes — 1 kg pack",
        category=Category(id=3, name="Vegetables"),
        category_id=3,
        farmer_name="Sunrise Organic Farm",
        description="Ripe tomatoes selected for curries and salads.",
        price=Decimal("75.00"),
        available_quantity=35,
        image_url="https://example.com/tomatoes.jpg",
        status=ProductStatus.ACTIVE,
        is_deleted=False,
        version=2,
    )


async def request_with_session(session: AsyncMock, method: str, path: str, **kwargs):
    async def override_session():
        yield session

    app.dependency_overrides[get_db_session] = override_session
    app.dependency_overrides[get_current_admin] = admin_user
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            return await client.request(method, path, **kwargs)
    finally:
        app.dependency_overrides.clear()


async def test_admin_list_includes_status_and_version() -> None:
    session = AsyncMock(spec=AsyncSession)
    session.scalar.return_value = 1
    session.scalars.return_value = [sample_product()]

    response = await request_with_session(session, "GET", "/api/v1/admin/products")

    assert response.status_code == 200
    assert response.json()["items"][0]["status"] == "active"
    assert response.json()["items"][0]["version"] == 2


async def test_create_product_validates_category_and_commits() -> None:
    session = AsyncMock(spec=AsyncSession)
    category = Category(id=3, name="Vegetables")
    session.get.return_value = category

    def assign_id(product: Product) -> None:
        product.id = 9
        product.version = 1

    session.add.side_effect = assign_id
    response = await request_with_session(
        session,
        "POST",
        "/api/v1/admin/products",
        json={
            "name": "Green Peas — 500 g pack",
            "category_id": 3,
            "farmer_name": "Hill View Farm",
            "description": "Fresh green peas packed on the morning of dispatch.",
            "price": "95.00",
            "available_quantity": 20,
            "image_url": "https://example.com/peas.jpg",
            "status": "inactive",
        },
    )

    assert response.status_code == 201
    assert response.json()["name"] == "Green Peas — 500 g pack"
    assert response.json()["status"] == "inactive"
    session.commit.assert_awaited_once()


async def test_descriptive_edit_does_not_change_stock_or_status() -> None:
    session = AsyncMock(spec=AsyncSession)
    product = sample_product()
    session.scalar.return_value = product

    response = await request_with_session(
        session,
        "PATCH",
        "/api/v1/admin/products/7",
        json={"name": "Premium Tomatoes — 1 kg pack", "price": "82.00"},
    )

    assert response.status_code == 200
    assert response.json()["name"] == "Premium Tomatoes — 1 kg pack"
    assert response.json()["available_quantity"] == 35
    assert response.json()["status"] == "active"
    assert product.version == 3


async def test_edit_rejects_explicit_null() -> None:
    session = AsyncMock(spec=AsyncSession)

    response = await request_with_session(
        session,
        "PATCH",
        "/api/v1/admin/products/7",
        json={"name": None},
    )

    assert response.status_code == 422
    session.scalar.assert_not_awaited()


async def test_status_change_is_explicit_and_increments_version() -> None:
    session = AsyncMock(spec=AsyncSession)
    product = sample_product()
    session.scalar.return_value = product

    response = await request_with_session(
        session,
        "PATCH",
        "/api/v1/admin/products/7/status",
        json={"status": "inactive"},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "inactive"
    assert response.json()["version"] == 3
    session.commit.assert_awaited_once()


async def test_stale_stock_update_returns_conflict() -> None:
    session = AsyncMock(spec=AsyncSession)
    product = sample_product()
    session.scalar.return_value = product

    response = await request_with_session(
        session,
        "PATCH",
        "/api/v1/admin/products/7/stock",
        json={"available_quantity": 12, "expected_version": 1},
    )

    assert response.status_code == 409
    assert product.available_quantity == 35
    session.commit.assert_not_awaited()


async def test_stock_update_uses_expected_version() -> None:
    session = AsyncMock(spec=AsyncSession)
    product = sample_product()
    session.scalar.return_value = product

    response = await request_with_session(
        session,
        "PATCH",
        "/api/v1/admin/products/7/stock",
        json={"available_quantity": 12, "expected_version": 2},
    )

    assert response.status_code == 200
    assert response.json()["available_quantity"] == 12
    assert response.json()["version"] == 3
    session.commit.assert_awaited_once()


async def test_delete_is_soft_delete() -> None:
    session = AsyncMock(spec=AsyncSession)
    product = sample_product()
    session.scalar.return_value = product

    response = await request_with_session(session, "DELETE", "/api/v1/admin/products/7")

    assert response.status_code == 204
    assert product.is_deleted is True
    assert product.version == 3
    session.commit.assert_awaited_once()


async def test_admin_product_routes_require_authentication() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/admin/products")

    assert response.status_code == 401
