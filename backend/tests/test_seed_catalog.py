from unittest.mock import AsyncMock

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Category
from app.schemas import ProductCreate
from app.scripts.seed_catalog import CATEGORY_NAMES, PRODUCTS, seed_products


def test_catalog_has_50_distinct_valid_products() -> None:
    assert len(PRODUCTS) == 50
    assert len({product["name"] for product in PRODUCTS}) == 50
    for product in PRODUCTS:
        fields = {key: value for key, value in product.items() if key != "category"}
        category_id = CATEGORY_NAMES.index(product["category"]) + 1
        ProductCreate(**fields, category_id=category_id, status="active")


async def test_seed_adds_only_missing_products_to_original_catalog() -> None:
    session = AsyncMock(spec=AsyncSession)
    existing_names = {product["name"] for product in PRODUCTS[:7]}
    session.scalars.return_value = existing_names
    categories = {name: Category(id=index, name=name)
                  for index, name in enumerate(CATEGORY_NAMES, start=1)}

    created = await seed_products(session, categories)

    assert created == 43
    added = [call.args[0] for call in session.add.call_args_list]
    assert len(added) == 43
    assert all(product.name not in existing_names for product in added)


async def test_seed_rerun_does_not_add_duplicates() -> None:
    session = AsyncMock(spec=AsyncSession)
    session.scalars.return_value = [product["name"] for product in PRODUCTS]

    assert await seed_products(session, {}) == 0
    session.add.assert_not_called()
