from typing import Annotated

from fastapi import APIRouter, Cookie, Depends, Header, HTTPException, Request, status
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.api.guest import check_guest_csrf, check_guest_origin, find_guest
from app.database import get_db_session
from app.models import Product, ProductStatus, WishlistItem
from app.schemas import WishlistRead

router = APIRouter(prefix="/wishlist", tags=["wishlist"])
DatabaseSession = Annotated[AsyncSession, Depends(get_db_session)]


async def read_wishlist(session: AsyncSession, guest_id: int) -> WishlistRead:
    query = (
        select(Product)
        .join(WishlistItem, WishlistItem.product_id == Product.id)
        .options(joinedload(Product.category))
        .where(
            WishlistItem.guest_session_id == guest_id,
            Product.status == ProductStatus.ACTIVE,
            Product.is_deleted.is_(False),
        )
        .order_by(WishlistItem.created_at.desc(), WishlistItem.id.desc())
    )
    products = list(await session.scalars(query))
    return WishlistRead(items=products, item_count=len(products))


@router.get("", response_model=WishlistRead)
async def get_wishlist(
    session: DatabaseSession,
    guest_token: Annotated[str | None, Cookie()] = None,
) -> WishlistRead:
    guest = await find_guest(session, guest_token)
    return await read_wishlist(session, guest.id)


@router.post("/{product_id}", response_model=WishlistRead)
async def add_to_wishlist(
    product_id: int,
    request: Request,
    session: DatabaseSession,
    guest_token: Annotated[str | None, Cookie()] = None,
    guest_csrf_token: Annotated[
        str | None, Header(alias="X-Guest-CSRF-Token")
    ] = None,
) -> WishlistRead:
    check_guest_origin(request)
    guest = await find_guest(session, guest_token, lock=True)
    check_guest_csrf(guest, guest_csrf_token)

    product = await session.get(Product, product_id)
    if product is None or product.is_deleted or product.status != ProductStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not available",
        )

    existing = await session.scalar(
        select(WishlistItem).where(
            WishlistItem.guest_session_id == guest.id,
            WishlistItem.product_id == product_id,
        )
    )
    if existing is None:
        session.add(WishlistItem(guest_session_id=guest.id, product_id=product_id))
        await session.flush()

    result = await read_wishlist(session, guest.id)
    await session.commit()
    return result


@router.delete("/{product_id}", response_model=WishlistRead)
async def remove_from_wishlist(
    product_id: int,
    request: Request,
    session: DatabaseSession,
    guest_token: Annotated[str | None, Cookie()] = None,
    guest_csrf_token: Annotated[
        str | None, Header(alias="X-Guest-CSRF-Token")
    ] = None,
) -> WishlistRead:
    check_guest_origin(request)
    guest = await find_guest(session, guest_token, lock=True)
    check_guest_csrf(guest, guest_csrf_token)

    await session.execute(
        delete(WishlistItem).where(
            WishlistItem.guest_session_id == guest.id,
            WishlistItem.product_id == product_id,
        )
    )
    await session.flush()
    result = await read_wishlist(session, guest.id)
    await session.commit()
    return result
