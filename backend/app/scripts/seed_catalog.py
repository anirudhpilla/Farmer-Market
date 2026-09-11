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
    # Additional demo products use labeled placeholder images.
    {
        "name": "Apples — 1 kg pack",
        "category": "Fruits",
        "farmer_name": "Kaveri Farms",
        "description": "Apples, sold as 1 kg pack for everyday cooking and meals.",
        "price": Decimal("180.00"),
        "available_quantity": 28,
        "image_url": "https://placehold.co/640x480/f5f7ef/27633c?text=Apples",
    },
    {
        "name": "Oranges — 1 kg pack",
        "category": "Fruits",
        "farmer_name": "Kaveri Farms",
        "description": "Oranges, sold as 1 kg pack for everyday cooking and meals.",
        "price": Decimal("95.00"),
        "available_quantity": 36,
        "image_url": "https://placehold.co/640x480/f5f7ef/27633c?text=Oranges",
    },
    {
        "name": "Guavas — 1 kg pack",
        "category": "Fruits",
        "farmer_name": "Kaveri Farms",
        "description": "Guavas, sold as 1 kg pack for everyday cooking and meals.",
        "price": Decimal("80.00"),
        "available_quantity": 20,
        "image_url": "https://placehold.co/640x480/f5f7ef/27633c?text=Guavas",
    },
    {
        "name": "Pomegranates — 500 g pack",
        "category": "Fruits",
        "farmer_name": "Kaveri Farms",
        "description": "Pomegranates, sold as 500 g pack for everyday cooking and meals.",
        "price": Decimal("120.00"),
        "available_quantity": 17,
        "image_url": "https://placehold.co/640x480/f5f7ef/27633c?text=Pomegranates",
    },
    {
        "name": "Papaya — 1 piece",
        "category": "Fruits",
        "farmer_name": "Kaveri Farms",
        "description": "Papaya, sold as 1 piece for everyday cooking and meals.",
        "price": Decimal("60.00"),
        "available_quantity": 12,
        "image_url": "https://placehold.co/640x480/f5f7ef/27633c?text=Papaya",
    },
    {
        "name": "Watermelon — 1 piece",
        "category": "Fruits",
        "farmer_name": "Kaveri Farms",
        "description": "Watermelon, sold as 1 piece for everyday cooking and meals.",
        "price": Decimal("110.00"),
        "available_quantity": 9,
        "image_url": "https://placehold.co/640x480/f5f7ef/27633c?text=Watermelon",
    },
    {
        "name": "Pineapple — 1 piece",
        "category": "Fruits",
        "farmer_name": "Kaveri Farms",
        "description": "Pineapple, sold as 1 piece for everyday cooking and meals.",
        "price": Decimal("85.00"),
        "available_quantity": 15,
        "image_url": "https://placehold.co/640x480/f5f7ef/27633c?text=Pineapple",
    },
    {
        "name": "Green Grapes — 500 g pack",
        "category": "Fruits",
        "farmer_name": "Kaveri Farms",
        "description": "Green Grapes, sold as 500 g pack for everyday cooking and meals.",
        "price": Decimal("70.00"),
        "available_quantity": 24,
        "image_url": "https://placehold.co/640x480/f5f7ef/27633c?text=Green%20Grapes",
    },
    {
        "name": "Black Grapes — 500 g pack",
        "category": "Fruits",
        "farmer_name": "Kaveri Farms",
        "description": "Black Grapes, sold as 500 g pack for everyday cooking and meals.",
        "price": Decimal("90.00"),
        "available_quantity": 18,
        "image_url": "https://placehold.co/640x480/f5f7ef/27633c?text=Black%20Grapes",
    },
    {
        "name": "Sweet Lime — 1 kg pack",
        "category": "Fruits",
        "farmer_name": "Kaveri Farms",
        "description": "Sweet Lime, sold as 1 kg pack for everyday cooking and meals.",
        "price": Decimal("100.00"),
        "available_quantity": 22,
        "image_url": "https://placehold.co/640x480/f5f7ef/27633c?text=Sweet%20Lime",
    },
    {
        "name": "Chikoo — 500 g pack",
        "category": "Fruits",
        "farmer_name": "Kaveri Farms",
        "description": "Chikoo, sold as 500 g pack for everyday cooking and meals.",
        "price": Decimal("55.00"),
        "available_quantity": 16,
        "image_url": "https://placehold.co/640x480/f5f7ef/27633c?text=Chikoo",
    },
    {
        "name": "Dragon Fruit — 1 piece",
        "category": "Fruits",
        "farmer_name": "Kaveri Farms",
        "description": "Dragon Fruit, sold as 1 piece for everyday cooking and meals.",
        "price": Decimal("130.00"),
        "available_quantity": 0,
        "image_url": "https://placehold.co/640x480/f5f7ef/27633c?text=Dragon%20Fruit",
    },
    {
        "name": "Basmati Rice — 1 kg pack",
        "category": "Grains",
        "farmer_name": "Green Valley Collective",
        "description": "Basmati Rice, sold as 1 kg pack for everyday cooking and meals.",
        "price": Decimal("160.00"),
        "available_quantity": 40,
        "image_url": "https://placehold.co/640x480/f5f7ef/27633c?text=Basmati%20Rice",
    },
    {
        "name": "Whole Wheat — 1 kg pack",
        "category": "Grains",
        "farmer_name": "Green Valley Collective",
        "description": "Whole Wheat, sold as 1 kg pack for everyday cooking and meals.",
        "price": Decimal("48.00"),
        "available_quantity": 60,
        "image_url": "https://placehold.co/640x480/f5f7ef/27633c?text=Whole%20Wheat",
    },
    {
        "name": "Ragi — 1 kg pack",
        "category": "Grains",
        "farmer_name": "Green Valley Collective",
        "description": "Ragi, sold as 1 kg pack for everyday cooking and meals.",
        "price": Decimal("75.00"),
        "available_quantity": 30,
        "image_url": "https://placehold.co/640x480/f5f7ef/27633c?text=Ragi",
    },
    {
        "name": "Jowar — 1 kg pack",
        "category": "Grains",
        "farmer_name": "Green Valley Collective",
        "description": "Jowar, sold as 1 kg pack for everyday cooking and meals.",
        "price": Decimal("65.00"),
        "available_quantity": 28,
        "image_url": "https://placehold.co/640x480/f5f7ef/27633c?text=Jowar",
    },
    {
        "name": "Bajra — 1 kg pack",
        "category": "Grains",
        "farmer_name": "Green Valley Collective",
        "description": "Bajra, sold as 1 kg pack for everyday cooking and meals.",
        "price": Decimal("58.00"),
        "available_quantity": 32,
        "image_url": "https://placehold.co/640x480/f5f7ef/27633c?text=Bajra",
    },
    {
        "name": "Foxtail Millet — 500 g pack",
        "category": "Grains",
        "farmer_name": "Green Valley Collective",
        "description": "Foxtail Millet, sold as 500 g pack for everyday cooking and meals.",
        "price": Decimal("85.00"),
        "available_quantity": 19,
        "image_url": "https://placehold.co/640x480/f5f7ef/27633c?text=Foxtail%20Millet",
    },
    {
        "name": "Little Millet — 500 g pack",
        "category": "Grains",
        "farmer_name": "Green Valley Collective",
        "description": "Little Millet, sold as 500 g pack for everyday cooking and meals.",
        "price": Decimal("80.00"),
        "available_quantity": 21,
        "image_url": "https://placehold.co/640x480/f5f7ef/27633c?text=Little%20Millet",
    },
    {
        "name": "Barley — 1 kg pack",
        "category": "Grains",
        "farmer_name": "Green Valley Collective",
        "description": "Barley, sold as 1 kg pack for everyday cooking and meals.",
        "price": Decimal("70.00"),
        "available_quantity": 14,
        "image_url": "https://placehold.co/640x480/f5f7ef/27633c?text=Barley",
    },
    {
        "name": "Rolled Oats — 500 g pack",
        "category": "Grains",
        "farmer_name": "Green Valley Collective",
        "description": "Rolled Oats, sold as 500 g pack for everyday cooking and meals.",
        "price": Decimal("95.00"),
        "available_quantity": 26,
        "image_url": "https://placehold.co/640x480/f5f7ef/27633c?text=Rolled%20Oats",
    },
    {
        "name": "Red Rice — 1 kg pack",
        "category": "Grains",
        "farmer_name": "Green Valley Collective",
        "description": "Red Rice, sold as 1 kg pack for everyday cooking and meals.",
        "price": Decimal("125.00"),
        "available_quantity": 18,
        "image_url": "https://placehold.co/640x480/f5f7ef/27633c?text=Red%20Rice",
    },
    {
        "name": "Mint — 1 bunch",
        "category": "Herbs",
        "farmer_name": "Urban Leaf Growers",
        "description": "Mint, sold as 1 bunch for everyday cooking and meals.",
        "price": Decimal("20.00"),
        "available_quantity": 25,
        "image_url": "https://placehold.co/640x480/f5f7ef/27633c?text=Mint",
    },
    {
        "name": "Curry Leaves — 100 g pack",
        "category": "Herbs",
        "farmer_name": "Urban Leaf Growers",
        "description": "Curry Leaves, sold as 100 g pack for everyday cooking and meals.",
        "price": Decimal("15.00"),
        "available_quantity": 30,
        "image_url": "https://placehold.co/640x480/f5f7ef/27633c?text=Curry%20Leaves",
    },
    {
        "name": "Basil — 1 bunch",
        "category": "Herbs",
        "farmer_name": "Urban Leaf Growers",
        "description": "Basil, sold as 1 bunch for everyday cooking and meals.",
        "price": Decimal("45.00"),
        "available_quantity": 12,
        "image_url": "https://placehold.co/640x480/f5f7ef/27633c?text=Basil",
    },
    {
        "name": "Dill — 1 bunch",
        "category": "Herbs",
        "farmer_name": "Urban Leaf Growers",
        "description": "Dill, sold as 1 bunch for everyday cooking and meals.",
        "price": Decimal("30.00"),
        "available_quantity": 10,
        "image_url": "https://placehold.co/640x480/f5f7ef/27633c?text=Dill",
    },
    {
        "name": "Parsley — 1 bunch",
        "category": "Herbs",
        "farmer_name": "Urban Leaf Growers",
        "description": "Parsley, sold as 1 bunch for everyday cooking and meals.",
        "price": Decimal("40.00"),
        "available_quantity": 8,
        "image_url": "https://placehold.co/640x480/f5f7ef/27633c?text=Parsley",
    },
    {
        "name": "Lemongrass — 100 g pack",
        "category": "Herbs",
        "farmer_name": "Urban Leaf Growers",
        "description": "Lemongrass, sold as 100 g pack for everyday cooking and meals.",
        "price": Decimal("35.00"),
        "available_quantity": 15,
        "image_url": "https://placehold.co/640x480/f5f7ef/27633c?text=Lemongrass",
    },
    {
        "name": "Fenugreek Leaves — 1 bunch",
        "category": "Herbs",
        "farmer_name": "Urban Leaf Growers",
        "description": "Fenugreek Leaves, sold as 1 bunch for everyday cooking and meals.",
        "price": Decimal("25.00"),
        "available_quantity": 20,
        "image_url": "https://placehold.co/640x480/f5f7ef/27633c?text=Fenugreek%20Leaves",
    },
    {
        "name": "Rosemary — 50 g pack",
        "category": "Herbs",
        "farmer_name": "Urban Leaf Growers",
        "description": "Rosemary, sold as 50 g pack for everyday cooking and meals.",
        "price": Decimal("65.00"),
        "available_quantity": 0,
        "image_url": "https://placehold.co/640x480/f5f7ef/27633c?text=Rosemary",
    },
    {
        "name": "Potatoes — 1 kg pack",
        "category": "Vegetables",
        "farmer_name": "Sunrise Organic Farm",
        "description": "Potatoes, sold as 1 kg pack for everyday cooking and meals.",
        "price": Decimal("40.00"),
        "available_quantity": 55,
        "image_url": "https://placehold.co/640x480/f5f7ef/27633c?text=Potatoes",
    },
    {
        "name": "Carrots — 500 g pack",
        "category": "Vegetables",
        "farmer_name": "Sunrise Organic Farm",
        "description": "Carrots, sold as 500 g pack for everyday cooking and meals.",
        "price": Decimal("35.00"),
        "available_quantity": 30,
        "image_url": "https://placehold.co/640x480/f5f7ef/27633c?text=Carrots",
    },
    {
        "name": "Beetroot — 500 g pack",
        "category": "Vegetables",
        "farmer_name": "Sunrise Organic Farm",
        "description": "Beetroot, sold as 500 g pack for everyday cooking and meals.",
        "price": Decimal("30.00"),
        "available_quantity": 23,
        "image_url": "https://placehold.co/640x480/f5f7ef/27633c?text=Beetroot",
    },
    {
        "name": "Cabbage — 1 piece",
        "category": "Vegetables",
        "farmer_name": "Sunrise Organic Farm",
        "description": "Cabbage, sold as 1 piece for everyday cooking and meals.",
        "price": Decimal("45.00"),
        "available_quantity": 18,
        "image_url": "https://placehold.co/640x480/f5f7ef/27633c?text=Cabbage",
    },
    {
        "name": "Cauliflower — 1 piece",
        "category": "Vegetables",
        "farmer_name": "Sunrise Organic Farm",
        "description": "Cauliflower, sold as 1 piece for everyday cooking and meals.",
        "price": Decimal("55.00"),
        "available_quantity": 16,
        "image_url": "https://placehold.co/640x480/f5f7ef/27633c?text=Cauliflower",
    },
    {
        "name": "Green Peas — 500 g pack",
        "category": "Vegetables",
        "farmer_name": "Sunrise Organic Farm",
        "description": "Green Peas, sold as 500 g pack for everyday cooking and meals.",
        "price": Decimal("65.00"),
        "available_quantity": 22,
        "image_url": "https://placehold.co/640x480/f5f7ef/27633c?text=Green%20Peas",
    },
    {
        "name": "French Beans — 500 g pack",
        "category": "Vegetables",
        "farmer_name": "Sunrise Organic Farm",
        "description": "French Beans, sold as 500 g pack for everyday cooking and meals.",
        "price": Decimal("50.00"),
        "available_quantity": 20,
        "image_url": "https://placehold.co/640x480/f5f7ef/27633c?text=French%20Beans",
    },
    {
        "name": "Okra — 500 g pack",
        "category": "Vegetables",
        "farmer_name": "Sunrise Organic Farm",
        "description": "Okra, sold as 500 g pack for everyday cooking and meals.",
        "price": Decimal("40.00"),
        "available_quantity": 25,
        "image_url": "https://placehold.co/640x480/f5f7ef/27633c?text=Okra",
    },
    {
        "name": "Brinjal — 500 g pack",
        "category": "Vegetables",
        "farmer_name": "Sunrise Organic Farm",
        "description": "Brinjal, sold as 500 g pack for everyday cooking and meals.",
        "price": Decimal("35.00"),
        "available_quantity": 19,
        "image_url": "https://placehold.co/640x480/f5f7ef/27633c?text=Brinjal",
    },
    {
        "name": "Bottle Gourd — 1 piece",
        "category": "Vegetables",
        "farmer_name": "Sunrise Organic Farm",
        "description": "Bottle Gourd, sold as 1 piece for everyday cooking and meals.",
        "price": Decimal("45.00"),
        "available_quantity": 11,
        "image_url": "https://placehold.co/640x480/f5f7ef/27633c?text=Bottle%20Gourd",
    },
    {
        "name": "Bitter Gourd — 500 g pack",
        "category": "Vegetables",
        "farmer_name": "Sunrise Organic Farm",
        "description": "Bitter Gourd, sold as 500 g pack for everyday cooking and meals.",
        "price": Decimal("40.00"),
        "available_quantity": 13,
        "image_url": "https://placehold.co/640x480/f5f7ef/27633c?text=Bitter%20Gourd",
    },
    {
        "name": "Cucumber — 500 g pack",
        "category": "Vegetables",
        "farmer_name": "Sunrise Organic Farm",
        "description": "Cucumber, sold as 500 g pack for everyday cooking and meals.",
        "price": Decimal("30.00"),
        "available_quantity": 28,
        "image_url": "https://placehold.co/640x480/f5f7ef/27633c?text=Cucumber",
    },
    {
        "name": "Green Capsicum — 500 g pack",
        "category": "Vegetables",
        "farmer_name": "Sunrise Organic Farm",
        "description": "Green Capsicum, sold as 500 g pack for everyday cooking and meals.",
        "price": Decimal("55.00"),
        "available_quantity": 17,
        "image_url": "https://placehold.co/640x480/f5f7ef/27633c?text=Green%20Capsicum",
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
