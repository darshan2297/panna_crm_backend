"""add is_free to order_items and first_order_only to promocodes

Revision ID: 75b3bb95bb3d
Revises:
Create Date: 2026-10-08 23:24:29.617625

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '75b3bb95bb3d'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('order_items', sa.Column('is_free', sa.Boolean(), nullable=False, server_default='0'))
    op.add_column('promocodes', sa.Column('first_order_only', sa.Boolean(), nullable=False, server_default='0'))


def downgrade() -> None:
    op.drop_column('promocodes', 'first_order_only')
    op.drop_column('order_items', 'is_free')
