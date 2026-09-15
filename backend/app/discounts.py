"""Scheduled prices; the database keeps the schedule across application restarts."""
import asyncio
import logging
from datetime import UTC, datetime
from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy import select

from app.database import SessionFactory

logger = logging.getLogger(__name__)


def current_price(product, now: datetime | None = None) -> Decimal:
    now = now or datetime.now(UTC)
    if product.regular_price is None:
        return product.price
    if product.discount_starts_at <= now < product.discount_ends_at:
        price = product.regular_price * (1 - product.discount_percent / Decimal(100))
        return max(Decimal("0.01"), price.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))
    return product.regular_price


def sync_price(product, now: datetime) -> None:
    price = current_price(product, now)
    if product.price != price:
        product.price = price
        product.version += 1


async def update_scheduled_prices() -> None:
    from app.models import Product

    async with SessionFactory.begin() as session:
        # Consistent lock order also matches checkout. Multiple workers are safe.
        products = await session.scalars(
            select(Product)
            .where(Product.regular_price.is_not(None), Product.is_deleted.is_(False))
            .order_by(Product.id)
            .with_for_update()
        )
        now = datetime.now(UTC)
        for product in products:
            sync_price(product, now)


async def run_discount_scheduler() -> None:
    while True:
        try:
            await update_scheduled_prices()
        except Exception:
            logger.exception("Scheduled price update failed; retrying in 15 seconds")
        await asyncio.sleep(15)
