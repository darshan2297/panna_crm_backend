"""snapshot cost_price on order_items, add other_expense to storefront config

Revision ID: c4d5e6f7a8b9
Revises: b3c4d5e6f7a8
Create Date: 2026-10-10

Adds:
  - order_items.cost_price: food cost snapshotted at order time so historical
    margin never changes when menu prices are later edited.
  - storefront_config.other_expense: flat per-order "other expenses"
    component used in the margin formula.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c4d5e6f7a8b9"
down_revision: Union[str, None] = "b3c4d5e6f7a8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "order_items",
        sa.Column("cost_price", sa.Float(), nullable=False, server_default="0"),
    )
    op.add_column(
        "storefront_config",
        sa.Column("other_expense", sa.Float(), nullable=False, server_default="0"),
    )


def downgrade() -> None:
    op.drop_column("order_items", "cost_price")
    op.drop_column("storefront_config", "other_expense")