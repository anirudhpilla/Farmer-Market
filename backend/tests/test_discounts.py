from datetime import UTC, datetime, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, patch

import pytest
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession
from test_admin_products_api import request_with_session, sample_product

from app.discounts import current_price, sync_price, update_scheduled_prices
from app.schemas import DiscountSchedule, ProductRead


def scheduled_product():
    product = sample_product()
    product.regular_price = Decimal('75.00')
    product.discount_percent = Decimal('10')
    product.discount_starts_at = datetime.now(UTC) - timedelta(minutes=1)
    product.discount_ends_at = datetime.now(UTC) + timedelta(minutes=1)
    return product


def test_exact_boundaries_and_no_compounding():
    product = scheduled_product()
    start, end = product.discount_starts_at, product.discount_ends_at
    assert current_price(product, start - timedelta(microseconds=1)) == Decimal('75')
    assert current_price(product, start) == Decimal('67.50')
    sync_price(product, start)
    version = product.version
    sync_price(product, start)
    assert product.price == Decimal('67.50')
    assert product.version == version
    # Expiry pricing is correct even before the scheduler has restored the column.
    assert current_price(product, end) == Decimal('75')
    sync_price(product, end)
    assert product.price == Decimal('75')


def test_public_response_uses_effective_price_before_job_runs():
    product = scheduled_product()
    assert product.price == Decimal('75')
    assert ProductRead.model_validate(product).model_dump(mode='json')['price'] == '67.50'


def test_rounding_and_minimum_price():
    product = scheduled_product()
    product.regular_price = Decimal('0.05')
    product.discount_percent = Decimal('50')
    assert current_price(product) == Decimal('0.03')
    product.regular_price = Decimal('0.01')
    product.discount_percent = Decimal('99.99')
    assert current_price(product) == Decimal('0.01')


@pytest.mark.parametrize('percent', ['0', '-1', '100', '101', '1.001'])
def test_invalid_percent(percent):
    now = datetime.now(UTC)
    with pytest.raises(ValidationError):
        DiscountSchedule(percent=percent, starts_at=now, ends_at=now + timedelta(hours=1))


def test_invalid_dates():
    now = datetime.now(UTC)
    for start, end in [(now, now), (now, now - timedelta(hours=1)),
                       (now.replace(tzinfo=None), now + timedelta(hours=1))]:
        with pytest.raises(ValidationError):
            DiscountSchedule(percent=10, starts_at=start, ends_at=end)


async def test_schedule_replace_base_edit_and_cancel():
    product = sample_product()
    session = AsyncMock(spec=AsyncSession)
    session.scalar.return_value = product
    now = datetime.now(UTC)
    body = {'percent': '10', 'starts_at': (now - timedelta(minutes=1)).isoformat(),
            'ends_at': (now + timedelta(hours=1)).isoformat()}
    path = '/api/v1/admin/products/7/discount'
    response = await request_with_session(session, 'PUT', path, json=body)
    assert response.status_code == 200
    assert response.json()['price'] == '67.50'
    body['percent'] = '20'
    response = await request_with_session(session, 'PUT', path, json=body)
    assert response.json()['price'] == '60.00'
    response = await request_with_session(session, 'PATCH', '/api/v1/admin/products/7',
                                          json={'price': '100.00'})
    assert response.json()['price'] == '80.00'
    response = await request_with_session(session, 'DELETE', path)
    assert response.json()['price'] == '100.00'
    assert response.json()['regular_price'] is None


async def test_scheduler_catches_up_after_downtime():
    product = scheduled_product()
    product.price = Decimal('67.50')
    product.discount_ends_at = datetime.now(UTC) - timedelta(seconds=1)
    session = AsyncMock(spec=AsyncSession)
    session.scalars.return_value = [product]
    with patch('app.discounts.SessionFactory') as factory:
        factory.begin.return_value.__aenter__.return_value = session
        await update_scheduled_prices()
    assert product.price == Decimal('75')


@pytest.mark.parametrize('expired,quoted,expected_status', [
    (False, '67.50', 201), (False, '75.00', 409), (True, '67.50', 409),
])
async def test_checkout_uses_schedule_even_when_job_is_late(
    monkeypatch, expired, quoted, expected_status,
):
    from test_orders_api import (
        CSRF,
        ORIGIN,
        checkout_body,
        guest_session,
        open_cart,
    )
    from test_orders_api import (
        request_with_session as checkout_request,
    )

    import app.api.orders as orders_api
    from app.models import CartItem

    product = scheduled_product()
    if expired:
        product.price = Decimal('67.50')
        product.discount_ends_at = datetime.now(UTC) - timedelta(seconds=1)
    session = AsyncMock(spec=AsyncSession)
    monkeypatch.setattr(orders_api, 'find_guest', AsyncMock(return_value=guest_session()))
    monkeypatch.setattr(orders_api, 'find_open_cart', AsyncMock(return_value=open_cart()))
    session.scalar.return_value = None
    session.scalars.side_effect = [
        [CartItem(id=4, cart_id=10, product_id=7, quantity=2)], [product],
    ]

    async def assign_ids():
        order = session.add.call_args.args[0]
        order.id = 22
        order.created_at = datetime.now(UTC)
        for item in order.items:
            item.id = 30

    session.flush.side_effect = assign_ids
    response = await checkout_request(
        session, 'POST', '/api/v1/orders/checkout', json=checkout_body(quoted),
        headers={'Origin': ORIGIN, 'X-Guest-CSRF-Token': CSRF,
                 'Idempotency-Key': 'scheduled-checkout'},
    )
    assert response.status_code == expected_status
    if expected_status == 201:
        assert response.json()['grand_total'] == '135.00'
        order = session.add.call_args.args[0]
        assert order.items[0].unit_price_snapshot == Decimal('67.50')
    else:
        session.commit.assert_not_awaited()
