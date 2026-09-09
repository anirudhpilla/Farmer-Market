import asyncio
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import SessionFactory, engine
from app.models import Category, Product, ProductStatus

CATEGORY_NAMES = ["Fruits", "Grains", "Herbs", "Vegetables"]

PRODUCTS = [
    {
        "name": "Alphonso Mangoes — 1 kg box",
        "category": "Fruits",
        "farmer_name": "Patil Family Farm",
        "description": "Sweet, aromatic mangoes packed as a one kilogram box.",
        "price": Decimal("420.00"),
        "available_quantity": 18,
        "image_url": "https://images.unsplash.com/photo-1553279768-865429fa0078",
    },
    {
        "name": "Bananas — 6 pieces",
        "category": "Fruits",
        "farmer_name": "Kaveri Farms",
        "description": "Naturally ripened bananas sold as a bunch of six.",
        "price": Decimal("65.00"),
        "available_quantity": 40,
        "image_url": "https://images.unsplash.com/photo-1571771894821-ce9b6c11b08e",
    },
    {
        "name": "Brown Rice — 1 kg pack",
        "category": "Grains",
        "farmer_name": "Green Valley Collective",
        "description": "Whole-grain brown rice cleaned and packed in one kilogram bags.",
        "price": Decimal("145.00"),
        "available_quantity": 25,
        "image_url": "https://images.unsplash.com/photo-1586201375761-83865001e31c",
    },
    {
        "name": "Coriander — 1 bunch",
        "category": "Herbs",
        "farmer_name": "Urban Leaf Growers",
        "description": "Fresh coriander harvested early in the morning.",
        "price": Decimal("30.00"),
        "available_quantity": 0,
        "image_url": "https://images.unsplash.com/photo-1601493700631-2b16ec4b4716",
    },
    {
        "name": "Red Onions — 1 kg pack",
        "category": "Vegetables",
        "farmer_name": "Nashik Harvest",
        "description": "Firm red onions suitable for everyday Indian cooking.",
        "price": Decimal("58.00"),
        "available_quantity": 32,
        "image_url": "https://images.unsplash.com/photo-1508747703725-719777637510",
    },
    {
        "name": "Spinach — 1 bunch",
        "category": "Vegetables",
        "farmer_name": "Urban Leaf Growers",
        "description": "Tender spinach leaves washed once and tied as a bunch.",
        "price": Decimal("42.00"),
        "available_quantity": 14,
        "image_url": "https://images.unsplash.com/photo-1576045057995-568f588f82fb",
    },
    {
        "name": "Tomatoes — 1 kg pack",
        "category": "Vegetables",
        "farmer_name": "Sunrise Organic Farm",
        "description": "Ripe, firm tomatoes selected for curries, salads, and sauces.",
        "price": Decimal("75.00"),
        "available_quantity": 35,
        "image_url": "https://images.unsplash.com/photo-1546094096-0df4bcaaa337",
    },
]


async def seed_categories(session: AsyncSession) -> dict[str, Category]:
    existing = await session.scalars(select(Category))
    categories = {category.name: category for category in existing}

    for name in CATEGORY_NAMES:
        if name not in categories:
            category = Category(name=name)
            session.add(category)
            categories[name] = category

    await session.flush()
    return categories


async def seed_products(
    session: AsyncSession,
    categories: dict[str, Category],
) -> int:
    existing_names = set(await session.scalars(select(Product.name)))
    created = 0

    for product_data in PRODUCTS:
        if product_data["name"] in existing_names:
            continue

        session.add(
            Product(
                name=product_data["name"],
                category_id=categories[product_data["category"]].id,
                farmer_name=product_data["farmer_name"],
                description=product_data["description"],
                price=product_data["price"],
                available_quantity=product_data["available_quantity"],
                image_url=product_data["image_url"],
                status=ProductStatus.ACTIVE,
            )
        )
        created += 1

    return created


async def main() -> None:
    async with SessionFactory.begin() as session:
        categories = await seed_categories(session)
        created_products = await seed_products(session, categories)

    await engine.dispose()
    print(f"Catalog seed complete: {created_products} products created")


if __name__ == "__main__":
    asyncio.run(main())
