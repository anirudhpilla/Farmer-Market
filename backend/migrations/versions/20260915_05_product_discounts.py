"""Add durable product discount schedules."""
import sqlalchemy as sa
from alembic import op

revision = "20260915_05"
down_revision = "20260911_04"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("products", sa.Column("regular_price", sa.Numeric(12, 2), nullable=True))
    op.add_column("products", sa.Column("discount_percent", sa.Numeric(5, 2), nullable=True))
    op.add_column("products", sa.Column("discount_starts_at", sa.DateTime(timezone=True)))
    op.add_column("products", sa.Column("discount_ends_at", sa.DateTime(timezone=True)))


def downgrade():
    op.execute("UPDATE products SET price = regular_price WHERE regular_price IS NOT NULL")
    for name in ("discount_ends_at", "discount_starts_at", "discount_percent", "regular_price"):
        op.drop_column("products", name)
