from datetime import UTC, datetime
from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Cookie, Depends, Header, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.guest import check_guest_csrf, check_guest_origin, find_guest
from app.database import get_db_session
from app.discounts import current_price
from app.models import Cart, CartItem, CartState, Product, ProductStatus
from app.schemas import CartItemCreate, CartItemRead, CartItemUpdate, CartRead

router = APIRouter(prefix="/cart", tags=["cart"])
DatabaseSession = Annotated[AsyncSession, Depends(get_db_session)]


async def find_open_cart(
    session: AsyncSession,
    guest_id: int,
    *,
    lock: bool = False,
) -> Cart | None:
    query = select(Cart).where(
        Cart.guest_session_id == guest_id,
        Cart.state == CartState.OPEN,
    )
    if lock:
        query = query.with_for_update()
    return await session.scalar(query)


async def read_cart(session: AsyncSession, cart: Cart | None) -> CartRead:
    if cart is None:
        return CartRead(id=None, version=0, items=[], item_count=0, grand_total=Decimal("0.00"))

    query = (
        select(CartItem, Product)
        .join(Product, Product.id == CartItem.product_id)
        .where(CartItem.cart_id == cart.id)
        .order_by(CartItem.id)
    )
    rows = (await session.execute(query)).all()
    items = []
    grand_total = Decimal("0.00")

    now = datetime.now(UTC)
    for cart_item, product in rows:
        price = current_price(product, now)
        issue = None
        if product.is_deleted or product.status != ProductStatus.ACTIVE:
            issue = "unavailable"
        elif cart_item.quantity > product.available_quantity:
            issue = "insufficient_stock"

        line_total = price * cart_item.quantity
        grand_total += line_total
        items.append(
            CartItemRead(
                id=cart_item.id,
                product_id=product.id,
                name=product.name,
                image_url=product.image_url,
                unit_price=price,
                quantity=cart_item.quantity,
                line_total=line_total,
                available_quantity=product.available_quantity,
                issue=issue,
            )
        )

    return CartRead(
        id=cart.id,
        version=cart.version,
        items=items,
        item_count=sum(item.quantity for item in items),
        grand_total=grand_total,
    )


def reject_unavailable_product(
    product: Product | None,
    quantity: int,
    *,
    hide_product: bool = True,
) -> None:
    if product is None or product.is_deleted or product.status != ProductStatus.ACTIVE:
        status_code = status.HTTP_404_NOT_FOUND if hide_product else status.HTTP_409_CONFLICT
        raise HTTPException(status_code=status_code, detail="Product not available")
    if quantity > product.available_quantity:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Only {product.available_quantity} units are currently available",
        )


@router.get("", response_model=CartRead)
async def get_cart(
    session: DatabaseSession,
    guest_token: Annotated[str | None, Cookie()] = None,
) -> CartRead:
    guest = await find_guest(session, guest_token)
    cart = await find_open_cart(session, guest.id)
    return await read_cart(session, cart)


@router.post("/items", response_model=CartRead)
async def add_cart_item(
    body: CartItemCreate,
    request: Request,
    session: DatabaseSession,
    guest_token: Annotated[str | None, Cookie()] = None,
    guest_csrf_token: Annotated[str | None, Header(alias="X-Guest-CSRF-Token")] = None,
) -> CartRead:
    check_guest_origin(request)
    guest = await find_guest(session, guest_token, lock=True)
    check_guest_csrf(guest, guest_csrf_token)

    product = await session.get(Product, body.product_id)
    reject_unavailable_product(product, body.quantity)
    cart = await find_open_cart(session, guest.id, lock=True)
    if cart is None:
        cart = Cart(guest_session_id=guest.id, state=CartState.OPEN, version=1)
        session.add(cart)
        await session.flush()

    cart_item = await session.scalar(
        select(CartItem)
        .where(CartItem.cart_id == cart.id, CartItem.product_id == body.product_id)
        .with_for_update()
    )
    resulting_quantity = body.quantity + (cart_item.quantity if cart_item else 0)
    reject_unavailable_product(product, resulting_quantity)

    if cart_item:
        cart_item.quantity = resulting_quantity
    else:
        session.add(CartItem(cart_id=cart.id, product_id=body.product_id, quantity=body.quantity))

    cart.version += 1
    await session.flush()
    result = await read_cart(session, cart)
    await session.commit()
    return result


@router.patch("/items/{item_id}", response_model=CartRead)
async def update_cart_item(
    item_id: int,
    body: CartItemUpdate,
    request: Request,
    session: DatabaseSession,
    guest_token: Annotated[str | None, Cookie()] = None,
    guest_csrf_token: Annotated[str | None, Header(alias="X-Guest-CSRF-Token")] = None,
) -> CartRead:
    check_guest_origin(request)
    guest = await find_guest(session, guest_token, lock=True)
    check_guest_csrf(guest, guest_csrf_token)
    cart = await find_open_cart(session, guest.id, lock=True)
    if cart is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cart item not found")

    cart_item = await session.scalar(
        select(CartItem)
        .where(CartItem.id == item_id, CartItem.cart_id == cart.id)
        .with_for_update()
    )
    if cart_item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cart item not found")

    product = await session.get(Product, cart_item.product_id)
    reject_unavailable_product(product, body.quantity, hide_product=False)
    cart_item.quantity = body.quantity
    cart.version += 1
    await session.flush()
    result = await read_cart(session, cart)
    await session.commit()
    return result


@router.delete("/items/{item_id}", response_model=CartRead)
async def remove_cart_item(
    item_id: int,
    request: Request,
    session: DatabaseSession,
    guest_token: Annotated[str | None, Cookie()] = None,
    guest_csrf_token: Annotated[str | None, Header(alias="X-Guest-CSRF-Token")] = None,
) -> CartRead:
    check_guest_origin(request)
    guest = await find_guest(session, guest_token, lock=True)
    check_guest_csrf(guest, guest_csrf_token)
    cart = await find_open_cart(session, guest.id, lock=True)
    if cart is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cart item not found")

    cart_item = await session.scalar(
        select(CartItem)
        .where(CartItem.id == item_id, CartItem.cart_id == cart.id)
        .with_for_update()
    )
    if cart_item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cart item not found")

    await session.delete(cart_item)
    cart.version += 1
    await session.flush()
    result = await read_cart(session, cart)
    await session.commit()
    return result
