from decimal import Decimal
from unittest.mock import AsyncMock

from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.catalog import escape_like_term
from app.database import get_db_session
from app.main import app
from app.models import Category, Product, ProductStatus


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
        version=1,
    )


async def test_product_list_forwards_filters_and_serializes_money() -> None:
    session = AsyncMock(spec=AsyncSession)
    session.scalar.return_value = 1
    session.scalars.return_value = [sample_product()]

    async def override_session():
        yield session

    app.dependency_overrides[get_db_session] = override_session

    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get(
                "/api/v1/products",
                params={"search": "tomato", "category_id": 3, "page_size": 6},
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["items"][0]["price"] == "75.00"
    assert response.json()["total_pages"] == 1
    session.scalar.assert_awaited_once()
    session.scalars.assert_awaited_once()


async def test_hidden_or_missing_product_returns_not_found() -> None:
    session = AsyncMock(spec=AsyncSession)
    session.scalar.return_value = None

    async def override_session():
        yield session

    app.dependency_overrides[get_db_session] = override_session

    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/v1/products/999")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 404
    assert response.json() == {"detail": "Product not found"}


async def test_product_list_rejects_oversized_page() -> None:
    session = AsyncMock(spec=AsyncSession)

    async def override_session():
        yield session

    app.dependency_overrides[get_db_session] = override_session

    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/v1/products", params={"page_size": 100})
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 422
    session.scalar.assert_not_awaited()


def test_like_search_characters_are_treated_as_literal_text() -> None:
    assert escape_like_term(r"50%_off\today") == r"50\%\_off\\today"
