from math import ceil
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.database import get_db_session
from app.models import Category, Product, ProductStatus
from app.schemas import CategoryRead, ProductPage, ProductRead

router = APIRouter(tags=["catalog"])
DatabaseSession = Annotated[AsyncSession, Depends(get_db_session)]


def escape_like_term(value: str) -> str:
    """Escape wildcard characters so search input is treated literally."""
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


@router.get("/categories", response_model=list[CategoryRead])
async def list_categories(session: DatabaseSession) -> list[CategoryRead]:
    result = await session.scalars(select(Category).order_by(Category.name))
    categories = list(result)
    return [CategoryRead.model_validate(category) for category in categories]


@router.get("/products", response_model=ProductPage)
async def list_products(
    session: DatabaseSession,
    search: Annotated[str | None, Query(min_length=1, max_length=100)] = None,
    category_id: Annotated[int | None, Query(ge=1)] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=24)] = 12,
) -> ProductPage:
    filters = [
        Product.status == ProductStatus.ACTIVE,
        Product.is_deleted.is_(False),
    ]

    if search and search.strip():
        escaped_search = escape_like_term(search.strip())
        filters.append(Product.name.ilike(f"%{escaped_search}%", escape="\\"))

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
    result = await session.scalars(query)

    return ProductPage(
        items=list(result),
        page=page,
        page_size=page_size,
        total=total,
        total_pages=ceil(total / page_size),
    )


@router.get("/products/{product_id}", response_model=ProductRead)
async def get_product(
    product_id: int,
    session: DatabaseSession,
) -> ProductRead:
    query = (
        select(Product)
        .options(joinedload(Product.category))
        .where(
            Product.id == product_id,
            Product.status == ProductStatus.ACTIVE,
            Product.is_deleted.is_(False),
        )
    )
    product = await session.scalar(query)

    if product is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found",
        )

    return ProductRead.model_validate(product)
