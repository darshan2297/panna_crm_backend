"""add gateway_order_id to orders

Revision ID: f7a8b9c0d1e2
Revises: e6f7a8b9c0d1
Create Date: 2026-10-11

Stores the Razorpay order id alongside the payment id so the CRM can show the
complete transaction trail (gateway order + payment + refund).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "f7a8b9c0d1e2"
down_revision: Union[str, None] = "e6f7a8b9c0d1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("orders", sa.Column("gateway_order_id", sa.String(100), nullable=True))


def downgrade() -> None:
    op.drop_column("orders", "gateway_order_id")