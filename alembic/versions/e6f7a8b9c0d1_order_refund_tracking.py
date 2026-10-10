"""add refund tracking columns to orders

Revision ID: e6f7a8b9c0d1
Revises: d5e6f7a8b9c0
Create Date: 2026-10-11

Persists structured refund data (gateway refund id, amount, timestamp) so the
CRM can surface "Refunded" state instead of relying only on free-text notes.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "e6f7a8b9c0d1"
down_revision: Union[str, None] = "d5e6f7a8b9c0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("orders", sa.Column("refund_id", sa.String(100), nullable=True))
    op.add_column(
        "orders",
        sa.Column("refund_amount", sa.Float(), nullable=True),
    )
    op.add_column("orders", sa.Column("refunded_at", sa.DateTime(), nullable=True))
    # Backfill structured refund data from the status-history note written by
    # refund_order (e.g. "Refund of Rs.149.00 issued via Razorpay
    # (refund_id: rfnd_xxx). Reason: ...") for orders already refunded.
    op.execute(
        """
        UPDATE orders
        SET refund_id = (
                SELECT substr(h.notes, instr(h.notes, 'refund_id: ') + 11,
                              instr(substr(h.notes, instr(h.notes, 'refund_id: ') + 11), ')') - 1)
                FROM order_status_history h
                WHERE h.order_id = orders.id AND h.notes LIKE '%refund_id: %'
                ORDER BY h.id DESC LIMIT 1
            ),
            refunded_at = (
                SELECT h.created_at FROM order_status_history h
                WHERE h.order_id = orders.id AND h.notes LIKE '%refund_id: %'
                ORDER BY h.id DESC LIMIT 1
            )
        WHERE payment_status = 'REFUNDED'
          AND EXISTS (SELECT 1 FROM order_status_history h
                      WHERE h.order_id = orders.id AND h.notes LIKE '%refund_id: %')
        """
    )


def downgrade() -> None:
    op.drop_column("orders", "refunded_at")
    op.drop_column("orders", "refund_amount")
    op.drop_column("orders", "refund_id")