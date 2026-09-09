from sqlalchemy import CheckConstraint

import app.models  # noqa: F401 -- populate the shared metadata
from app.database import Base


def test_core_tables_are_registered() -> None:
    expected_tables = {"categories", "products"}

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
