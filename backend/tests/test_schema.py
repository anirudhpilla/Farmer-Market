from sqlalchemy import CheckConstraint

import app.models  # noqa: F401 -- populate the shared metadata
from app.database import Base


def test_core_tables_are_registered() -> None:
    expected_tables = {
        "categories",
        "cart_items",
        "carts",
        "guest_sessions",
        "order_items",
        "orders",
        "products",
        "refresh_sessions",
        "refresh_tokens",
        "users",
    }

    assert expected_tables == set(Base.metadata.tables)


def test_product_values_have_database_constraints() -> None:
    product_constraints = Base.metadata.tables["products"].constraints

    product_check_names = {
        constraint.name
        for constraint in product_constraints
        if isinstance(constraint, CheckConstraint)
    }
    assert "ck_products_price_positive" in product_check_names
    assert "ck_products_quantity_non_negative" in product_check_names


def test_cart_quantity_has_database_constraint() -> None:
    cart_item_constraints = Base.metadata.tables["cart_items"].constraints
    check_names = {
        constraint.name
        for constraint in cart_item_constraints
        if isinstance(constraint, CheckConstraint)
    }
    assert "ck_cart_items_quantity_positive" in check_names


def test_order_snapshots_have_database_constraints() -> None:
    constraints = Base.metadata.tables["order_items"].constraints
    check_names = {
        constraint.name for constraint in constraints if isinstance(constraint, CheckConstraint)
    }
    assert "ck_order_items_quantity_positive" in check_names
    assert "ck_order_items_price_positive" in check_names
    order_constraints = Base.metadata.tables["orders"].constraints
    order_check_names = {
        constraint.name
        for constraint in order_constraints
        if isinstance(constraint, CheckConstraint)
    }
    assert "ck_orders_grand_total_positive" in order_check_names
