"""add max_discount_amount cap for percentage promos

Revision ID: c7d1e3f9a2b4
Revises: b2c4d8e1f7a3
Create Date: 2026-10-09

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'c7d1e3f9a2b4'
down_revision: Union[str, None] = 'b2c4d8e1f7a3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('promocodes', sa.Column('max_discount_amount', sa.Float(), nullable=True))


def downgrade() -> None:
    op.drop_column('promocodes', 'max_discount_amount')