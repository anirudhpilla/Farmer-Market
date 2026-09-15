from datetime import UTC, datetime
from math import ceil
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.api.auth import get_current_admin
from app.api.catalog import escape_like_term
from app.database import get_db_session
from app.discounts import current_price
from app.models import Category, Product, ProductStatus, User
from app.schemas import (
    AdminProductPage,
    AdminProductRead,
    DiscountSchedule,
    ProductCreate,
    ProductStatusUpdate,
    ProductStockUpdate,
    ProductUpdate,
)

router = APIRouter(prefix="/admin/products", tags=["admin products"])
DatabaseSession = Annotated[AsyncSession, Depends(get_db_session)]
CurrentAdmin = Annotated[User, Depends(get_current_admin)]


async def find_product(
    session: AsyncSession,
    product_id: int,
    *,
    lock: bool = False,
) -> Product:
    query = (
        select(Product)
        .options(joinedload(Product.category))
        .where(Product.id == product_id, Product.is_deleted.is_(False))
    )
    if lock:
        query = query.with_for_update(of=Product)

    product = await session.scalar(query)
    if product is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    return product


async def find_category(session: AsyncSession, category_id: int) -> Category:
    category = await session.get(Category, category_id)
    if category is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Category does not exist",
        )
    return category


@router.get("", response_model=AdminProductPage)
async def list_admin_products(
    session: DatabaseSession,
    _admin: CurrentAdmin,
    search: Annotated[str | None, Query(min_length=1, max_length=100)] = None,
    category_id: Annotated[int | None, Query(ge=1)] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=50)] = 20,
) -> AdminProductPage:
    filters = [Product.is_deleted.is_(False)]
    if search and search.strip():
        term = escape_like_term(search.strip())
        filters.append(Product.name.ilike(f"%{term}%", escape="\\"))
    if category_id is not None:
        filters.append(Product.category_id == category_id)

    total = await session.scalar(select(func.count()).select_from(Product).where(*filters))
    total = total or 0

    query = (
        select(Product)
        .options(joinedload(Product.category))
        .where(*filters)
        .order_by(Product.name, Product.id)
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    products = list(await session.scalars(query))
    return AdminProductPage(
        items=products,
        page=page,
        page_size=page_size,
        total=total,
        total_pages=ceil(total / page_size),
    )


@router.get("/{product_id}", response_model=AdminProductRead)
async def get_admin_product(
    product_id: int,
    session: DatabaseSession,
    _admin: CurrentAdmin,
) -> Product:
    return await find_product(session, product_id)


@router.post("", response_model=AdminProductRead, status_code=status.HTTP_201_CREATED)
async def create_product(
    body: ProductCreate,
    session: DatabaseSession,
    _admin: CurrentAdmin,
) -> Product:
    category = await find_category(session, body.category_id)
    product = Product(
        name=body.name,
        category_id=category.id,
        farmer_name=body.farmer_name,
        description=body.description,
        price=body.price,
        available_quantity=body.available_quantity,
        image_url=str(body.image_url),
        status=ProductStatus(body.status),
        category=category,
    )
    session.add(product)
    await session.commit()
    return product


@router.patch("/{product_id}", response_model=AdminProductRead)
async def update_product(
    product_id: int,
    body: ProductUpdate,
    session: DatabaseSession,
    _admin: CurrentAdmin,
) -> Product:
    product = await find_product(session, product_id, lock=True)
    changes = body.model_dump(exclude_unset=True)

    if "category_id" in changes:
        category = await find_category(session, changes["category_id"])
        product.category = category

    if "image_url" in changes:
        changes["image_url"] = str(changes["image_url"])

    if "price" in changes and product.regular_price is not None:
        product.regular_price = changes.pop("price")
        product.price = current_price(product)

    for field, value in changes.items():
        setattr(product, field, value)

    product.version += 1
    await session.commit()
    return product


@router.patch("/{product_id}/status", response_model=AdminProductRead)
async def update_product_status(
    product_id: int,
    body: ProductStatusUpdate,
    session: DatabaseSession,
    _admin: CurrentAdmin,
) -> Product:
    product = await find_product(session, product_id, lock=True)
    product.status = ProductStatus(body.status)
    product.version += 1
    await session.commit()
    return product


@router.patch("/{product_id}/stock", response_model=AdminProductRead)
async def update_product_stock(
    product_id: int,
    body: ProductStockUpdate,
    session: DatabaseSession,
    _admin: CurrentAdmin,
) -> Product:
    product = await find_product(session, product_id, lock=True)
    if product.version != body.expected_version:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Product changed; reload it before updating stock",
        )

    product.available_quantity = body.available_quantity
    product.version += 1
    await session.commit()
    return product


@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_product(
    product_id: int,
    session: DatabaseSession,
    _admin: CurrentAdmin,
) -> None:
    product = await find_product(session, product_id, lock=True)
    product.is_deleted = True
    product.version += 1
    await session.commit()


@router.put("/{product_id}/discount", response_model=AdminProductRead)
async def schedule_discount(
    product_id: int, body: DiscountSchedule, session: DatabaseSession, _admin: CurrentAdmin,
) -> Product:
    product = await find_product(session, product_id, lock=True)
    # Replacing a schedule must never compound the previous discount.
    if product.regular_price is None:
        product.regular_price = product.price
    product.discount_percent = body.percent
    product.discount_starts_at = body.starts_at
    product.discount_ends_at = body.ends_at
    product.price = current_price(product, datetime.now(UTC))
    product.version += 1
    await session.commit()
    return product


@router.delete("/{product_id}/discount", response_model=AdminProductRead)
async def cancel_discount(
    product_id: int, session: DatabaseSession, _admin: CurrentAdmin,
) -> Product:
    product = await find_product(session, product_id, lock=True)
    if product.regular_price is not None:
        product.price = product.regular_price
        product.regular_price = None
        product.discount_percent = None
        product.discount_starts_at = None
        product.discount_ends_at = None
        product.version += 1
    await session.commit()
    return product
