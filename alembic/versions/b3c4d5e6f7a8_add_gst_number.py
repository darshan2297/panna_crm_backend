"""add gst_number to storefront config

Revision ID: b3c4d5e6f7a8
Revises: e9f0a1b2c3d4
Create Date: 2026-10-10

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'b3c4d5e6f7a8'
down_revision: Union[str, None] = 'e9f0a1b2c3d4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('storefront_config', sa.Column('gst_number', sa.String(50), nullable=True))


def downgrade() -> None:
    op.drop_column('storefront_config', 'gst_number')
