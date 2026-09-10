import hashlib
import json
from decimal import Decimal
from math import ceil
from typing import Annotated

from fastapi import (
    APIRouter,
    Cookie,
    Depends,
    Header,
    HTTPException,
    Query,
    Request,
    Response,
    status,
)
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.auth import get_current_admin
from app.api.cart import find_open_cart
from app.api.guest import check_guest_csrf, check_guest_origin, find_guest
from app.database import get_db_session
from app.models import (
    CartItem,
    CartState,
    Order,
    OrderItem,
    OrderStatus,
    Product,
    ProductStatus,
    User,
)
from app.schemas import CheckoutRequest, OrderItemRead, OrderPage, OrderRead

router = APIRouter(tags=["orders"])
DatabaseSession = Annotated[AsyncSession, Depends(get_db_session)]
CurrentAdmin = Annotated[User, Depends(get_current_admin)]


def checkout_fingerprint(body: CheckoutRequest) -> str:
    items = sorted(
        (
            {
                "product_id": item.product_id,
                "quantity": item.quantity,
                "unit_price": f"{item.unit_price:.2f}",
            }
            for item in body.items
        ),
        key=lambda item: item["product_id"],
    )
    value = json.dumps(
        {"expected_cart_version": body.expected_cart_version, "items": items},
        separators=(",", ":"),
        sort_keys=True,
    )
    return hashlib.sha256(value.encode()).hexdigest()


def order_response(order: Order) -> OrderRead:
    items = [
        OrderItemRead(
            id=item.id,
            product_id=item.product_id,
            product_name=item.product_name_snapshot,
            unit_price=item.unit_price_snapshot,
            quantity=item.quantity,
            line_total=item.unit_price_snapshot * item.quantity,
        )
        for item in order.items
    ]
    return OrderRead(
        id=order.id,
        status=order.status.value,
        currency=order.currency,
        grand_total=order.grand_total,
        item_count=sum(item.quantity for item in items),
        items=items,
        created_at=order.created_at,
    )


async def find_order(session: AsyncSession, order_id: int, guest_id: int | None = None) -> Order:
    query = select(Order).options(selectinload(Order.items)).where(Order.id == order_id)
    if guest_id is not None:
        query = query.where(Order.guest_session_id == guest_id)
    order = await session.scalar(query)
    if order is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
    return order


@router.post(
    "/orders/checkout",
    response_model=OrderRead,
    status_code=status.HTTP_201_CREATED,
)
async def checkout(
    body: CheckoutRequest,
    request: Request,
    response: Response,
    session: DatabaseSession,
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key", min_length=8, max_length=100)],
    guest_token: Annotated[str | None, Cookie()] = None,
    guest_csrf_token: Annotated[str | None, Header(alias="X-Guest-CSRF-Token")] = None,
) -> OrderRead:
    check_guest_origin(request)
    guest = await find_guest(session, guest_token, lock=True)
    check_guest_csrf(guest, guest_csrf_token)
    fingerprint = checkout_fingerprint(body)

    existing_order = await session.scalar(
        select(Order)
        .options(selectinload(Order.items))
        .where(
            Order.guest_session_id == guest.id,
            Order.idempotency_key == idempotency_key,
        )
    )
    if existing_order:
        if existing_order.request_fingerprint != fingerprint:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="This idempotency key was already used for a different checkout",
            )
        response.status_code = status.HTTP_200_OK
        return order_response(existing_order)

    cart = await find_open_cart(session, guest.id, lock=True)
    if cart is None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="The cart is empty")
    if cart.version != body.expected_cart_version:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="The cart changed; review it before checking out",
        )

    cart_items = list(
        await session.scalars(
            select(CartItem).where(CartItem.cart_id == cart.id).order_by(CartItem.product_id)
        )
    )
    if not cart_items:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="The cart is empty")

    expected = {item.product_id: item for item in body.items}
    actual_quantities = {item.product_id: item.quantity for item in cart_items}
    expected_quantities = {product_id: item.quantity for product_id, item in expected.items()}
    if actual_quantities != expected_quantities:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="The cart contents changed; review them before checking out",
        )

    product_ids = sorted(actual_quantities)
    products = list(
        await session.scalars(
            select(Product)
            .where(Product.id.in_(product_ids))
            .order_by(Product.id)
            .with_for_update()
        )
    )
    if [product.id for product in products] != product_ids:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="A product is unavailable")

    for product in products:
        quantity = actual_quantities[product.id]
        if product.is_deleted or product.status != ProductStatus.ACTIVE:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"{product.name} is no longer available",
            )
        if quantity > product.available_quantity:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Only {product.available_quantity} units of {product.name} remain",
            )
        if product.price != expected[product.id].unit_price:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"The price of {product.name} changed; review the cart again",
            )

    grand_total = sum(
        (product.price * actual_quantities[product.id] for product in products),
        start=Decimal("0.00"),
    )
    order = Order(
        cart_id=cart.id,
        guest_session_id=guest.id,
        status=OrderStatus.CONFIRMED,
        currency="INR",
        grand_total=grand_total,
        idempotency_key=idempotency_key,
        request_fingerprint=fingerprint,
    )
    for product in products:
        quantity = actual_quantities[product.id]
        product.available_quantity -= quantity
        product.version += 1
        order.items.append(
            OrderItem(
                product_id=product.id,
                product_name_snapshot=product.name,
                unit_price_snapshot=product.price,
                quantity=quantity,
            )
        )

    cart.state = CartState.CONVERTED
    cart.version += 1
    session.add(order)
    await session.flush()
    await session.commit()
    return order_response(order)


@router.get("/orders", response_model=OrderPage)
async def list_guest_orders(
    session: DatabaseSession,
    guest_token: Annotated[str | None, Cookie()] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=50)] = 20,
) -> OrderPage:
    guest = await find_guest(session, guest_token)
    owned = Order.guest_session_id == guest.id
    total = await session.scalar(
        select(func.count()).select_from(Order).where(owned)
    ) or 0
    orders = list(
        await session.scalars(
            select(Order)
            .options(selectinload(Order.items))
            .where(owned)
            .order_by(Order.created_at.desc(), Order.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    )
    return OrderPage(
        items=[order_response(order) for order in orders],
        page=page,
        page_size=page_size,
        total=total,
        total_pages=ceil(total / page_size),
    )


@router.get("/orders/{order_id}", response_model=OrderRead)
async def get_guest_order(
    order_id: int,
    session: DatabaseSession,
    guest_token: Annotated[str | None, Cookie()] = None,
) -> OrderRead:
    guest = await find_guest(session, guest_token)
    return order_response(await find_order(session, order_id, guest.id))


@router.get("/admin/orders", response_model=OrderPage)
async def list_admin_orders(
    session: DatabaseSession,
    _admin: CurrentAdmin,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=50)] = 20,
) -> OrderPage:
    total = await session.scalar(select(func.count()).select_from(Order)) or 0
    orders = list(
        await session.scalars(
            select(Order)
            .options(selectinload(Order.items))
            .order_by(Order.created_at.desc(), Order.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    )
    return OrderPage(
        items=[order_response(order) for order in orders],
        page=page,
        page_size=page_size,
        total=total,
        total_pages=ceil(total / page_size),
    )


@router.get("/admin/orders/{order_id}", response_model=OrderRead)
async def get_admin_order(
    order_id: int,
    session: DatabaseSession,
    _admin: CurrentAdmin,
) -> OrderRead:
    return order_response(await find_order(session, order_id))
