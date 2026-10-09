"""advanced promo codes: category, private flag, terms, discount_on, thresholds, events, usages

Revision ID: b2c4d8e1f7a3
Revises: 75b3bb95bb3d
Create Date: 2026-10-09

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'b2c4d8e1f7a3'
down_revision: Union[str, None] = '75b3bb95bb3d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- promocodes: advanced criteria ---
    op.add_column('promocodes', sa.Column('category', sa.String(30), nullable=False, server_default='general'))
    op.add_column('promocodes', sa.Column('is_private', sa.Boolean(), nullable=False, server_default='0'))
    op.add_column('promocodes', sa.Column('terms_conditions', sa.Text(), nullable=True))
    op.add_column('promocodes', sa.Column('discount_on', sa.String(20), nullable=False, server_default='amount'))
    op.add_column('promocodes', sa.Column('min_quantity', sa.Integer(), nullable=True))
    op.add_column('promocodes', sa.Column('max_quantity', sa.Integer(), nullable=True))
    op.add_column('promocodes', sa.Column('max_order_value', sa.Float(), nullable=True))
    op.add_column('promocodes', sa.Column('customer_type', sa.String(30), nullable=False, server_default='all'))

    with op.batch_alter_table('promocodes') as batch_op:
        batch_op.create_index('ix_promocodes_category', ['category'], unique=False)

    # --- promo_events: campaign windows ---
    op.create_table(
        'promo_events',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('promo_code_id', sa.Integer(), sa.ForeignKey('promocodes.id', ondelete='CASCADE'), nullable=False),
        sa.Column('event_title', sa.String(150), nullable=False),
        sa.Column('start_date', sa.DateTime(), nullable=False),
        sa.Column('end_date', sa.DateTime(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
    )
    op.create_index('ix_promo_events_promo_code_id', 'promo_events', ['promo_code_id'], unique=False)

    # --- promo_code_usages: per-customer redemption log ---
    op.create_table(
        'promo_code_usages',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('promo_code_id', sa.Integer(), sa.ForeignKey('promocodes.id', ondelete='CASCADE'), nullable=False),
        sa.Column('customer_phone', sa.String(10), nullable=False),
        sa.Column('order_id', sa.Integer(), sa.ForeignKey('orders.id', ondelete='SET NULL'), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
    )
    op.create_index('ix_promo_code_usages_promo_code_id', 'promo_code_usages', ['promo_code_id'], unique=False)
    op.create_index('ix_promo_code_usages_customer_phone', 'promo_code_usages', ['customer_phone'], unique=False)
    # One redemption per (promo, phone) — makes concurrent double-use impossible.
    op.create_index(
        'uq_promo_usage_per_customer',
        'promo_code_usages',
        ['promo_code_id', 'customer_phone'],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index('uq_promo_usage_per_customer', table_name='promo_code_usages')
    op.drop_index('ix_promo_code_usages_customer_phone', table_name='promo_code_usages')
    op.drop_index('ix_promo_code_usages_promo_code_id', table_name='promo_code_usages')
    op.drop_table('promo_code_usages')

    op.drop_index('ix_promo_events_promo_code_id', table_name='promo_events')
    op.drop_table('promo_events')

    with op.batch_alter_table('promocodes') as batch_op:
        batch_op.drop_index('ix_promocodes_category')

    op.drop_column('promocodes', 'customer_type')
    op.drop_column('promocodes', 'max_order_value')
    op.drop_column('promocodes', 'max_quantity')
    op.drop_column('promocodes', 'min_quantity')
    op.drop_column('promocodes', 'discount_on')
    op.drop_column('promocodes', 'terms_conditions')
    op.drop_column('promocodes', 'is_private')
    op.drop_column('promocodes', 'category')