"""Add guest wishlists.

Revision ID: 20260915_06
Revises: 20260915_05
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260915_06"
down_revision: str | None = "20260915_05"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "wishlist_items",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "guest_session_id",
            sa.Integer(),
            sa.ForeignKey("guest_sessions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "product_id",
            sa.Integer(),
            sa.ForeignKey("products.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint(
            "guest_session_id",
            "product_id",
            name="uq_wishlist_items_guest_product",
        ),
    )
    op.create_index(
        "ix_wishlist_items_guest_session_id",
        "wishlist_items",
        ["guest_session_id"],
    )
    op.create_index(
        "ix_wishlist_items_product_id",
        "wishlist_items",
        ["product_id"],
    )


def downgrade() -> None:
    op.drop_table("wishlist_items")
