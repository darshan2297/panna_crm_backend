"""online payment fees (transaction fee, GST, VAS) + gateway refund reference

Revision ID: e9f0a1b2c3d4
Revises: d4e8f1a2b6c9
Create Date: 2026-10-10

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'e9f0a1b2c3d4'
down_revision: Union[str, None] = 'd4e8f1a2b6c9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Storefront pricing config: online-payment surcharges + VAS fee.
    op.add_column('storefront_config', sa.Column('transaction_fee_percent', sa.Float(), nullable=False, server_default='0'))
    op.add_column('storefront_config', sa.Column('gst_percent', sa.Float(), nullable=False, server_default='5'))
    op.add_column('storefront_config', sa.Column('vas_fee', sa.Float(), nullable=False, server_default='0'))

    # Per-order fee breakdown + gateway reference used for refunds.
    op.add_column('orders', sa.Column('transaction_fee', sa.Float(), nullable=False, server_default='0'))
    op.add_column('orders', sa.Column('vas_fee', sa.Float(), nullable=False, server_default='0'))
    op.add_column('orders', sa.Column('gateway', sa.String(50), nullable=True))
    op.add_column('orders', sa.Column('gateway_payment_id', sa.String(100), nullable=True))
    op.create_index('ix_orders_gateway_payment_id', 'orders', ['gateway_payment_id'])


def downgrade() -> None:
    op.drop_index('ix_orders_gateway_payment_id', table_name='orders')
    op.drop_column('orders', 'gateway_payment_id')
    op.drop_column('orders', 'gateway')
    op.drop_column('orders', 'vas_fee')
    op.drop_column('orders', 'transaction_fee')
    op.drop_column('storefront_config', 'vas_fee')
    op.drop_column('storefront_config', 'gst_percent')
    op.drop_column('storefront_config', 'transaction_fee_percent')
