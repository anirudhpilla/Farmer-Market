"""Add guest sessions and carts.

Revision ID: 20260910_03
Revises: 20260909_02
Create Date: 2026-09-10
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260910_03"
down_revision: str | None = "20260909_02"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

cart_state = sa.Enum("open", "converted", name="cart_state")


def upgrade() -> None:
    op.create_table(
        "guest_sessions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("token_digest", sa.String(64), nullable=False, unique=True),
        sa.Column("csrf_digest", sa.String(64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    op.create_table(
        "carts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("guest_session_id", sa.Integer(), nullable=False),
        sa.Column("state", cart_state, nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["guest_session_id"], ["guest_sessions.id"], ondelete="RESTRICT"),
    )
    op.create_index("ix_carts_guest_session_id", "carts", ["guest_session_id"])
    op.create_index(
        "uq_carts_one_open_per_guest",
        "carts",
        ["guest_session_id"],
        unique=True,
        postgresql_where=sa.text("state = 'open'"),
    )

    op.create_table(
        "cart_items",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("cart_id", sa.Integer(), nullable=False),
        sa.Column("product_id", sa.Integer(), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.CheckConstraint("quantity > 0", name="ck_cart_items_quantity_positive"),
        sa.ForeignKeyConstraint(["cart_id"], ["carts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("cart_id", "product_id", name="uq_cart_items_cart_product"),
    )


def downgrade() -> None:
    op.drop_table("cart_items")
    op.drop_index("uq_carts_one_open_per_guest", table_name="carts")
    op.drop_table("carts")
    op.drop_table("guest_sessions")
    cart_state.drop(op.get_bind(), checkfirst=True)
