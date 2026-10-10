"""add order_type to orders

Revision ID: a1b2c3d4e5f6
Revises: f7a8b9c0d1e2
Create Date: 2026-10-11

Stores whether an order is DELIVERY or PICKUP so the storefront can show real
fulfilment-preference statistics instead of hardcoded percentages.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, None] = "f7a8b9c0d1e2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "orders",
        sa.Column("order_type", sa.String(20), nullable=True),
    )
    # Backfill historical website orders. Pickup orders were stored with a
    # "Pickup from kitchen..." marker in delivery_address, so match that first
    # and only treat a genuine street address as DELIVERY.
    op.execute(
        """
        UPDATE orders
        SET order_type = CASE
            WHEN delivery_address IS NULL OR delivery_address = '' THEN 'PICKUP'
            WHEN lower(delivery_address) LIKE 'pickup from kitchen%' THEN 'PICKUP'
            ELSE 'DELIVERY' END
        WHERE platform = 'WEBSITE' AND order_type IS NULL
        """
    )