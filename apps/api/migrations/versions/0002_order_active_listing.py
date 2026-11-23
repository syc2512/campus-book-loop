"""allow a new order after a listing is cancelled or refunded

Revision ID: 0002_order_active_listing
Revises: 38a29d388795
Create Date: 2026-11-22

The first schema made ``orders.listing_id`` globally unique, which prevented a
listing from being purchased again after cancellation or refund. This migration
replaces that constraint with a partial unique index covering only non-terminal
orders (``pending_payment`` and ``paid``).

Downgrade restores the global constraint and therefore requires at most one
order per listing; remove historical duplicates before downgrading.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002_order_active_listing"
down_revision: str | None = "38a29d388795"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

NAMING_CONVENTION = {"uq": "uq_%(table_name)s_%(column_0_name)s"}
ACTIVE_ORDER_CONDITION = sa.text("status IN ('pending_payment', 'paid')")


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        # SQLite cannot drop constraints in place; batch mode rebuilds the table.
        with op.batch_alter_table(
            "orders", naming_convention=NAMING_CONVENTION
        ) as batch_op:
            batch_op.drop_constraint("uq_orders_listing_id", type_="unique")
    else:
        op.drop_constraint("orders_listing_id_key", "orders", type_="unique")

    op.create_index(
        "uq_orders_active_listing",
        "orders",
        ["listing_id"],
        unique=True,
        sqlite_where=ACTIVE_ORDER_CONDITION,
        postgresql_where=ACTIVE_ORDER_CONDITION,
    )


def downgrade() -> None:
    op.drop_index("uq_orders_active_listing", table_name="orders")

    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        with op.batch_alter_table(
            "orders", naming_convention=NAMING_CONVENTION
        ) as batch_op:
            batch_op.create_unique_constraint("uq_orders_listing_id", ["listing_id"])
    else:
        op.create_unique_constraint(
            "orders_listing_id_key", "orders", ["listing_id"]
        )
