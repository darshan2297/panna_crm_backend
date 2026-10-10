"""revision identifier: d4e8f1a2b6c9
Revises: c7d1e3f9a2b4
Create Date: 2026-10-10

Role-based access control: roles, role_permissions and users.role_id.
"""

import sqlalchemy as sa
from alembic import op

revision = "d4e8f1a2b6c9"
down_revision = "c7d1e3f9a2b4"
branch_labels = None
depends_on = None

# Matches TimestampMixin so the tables are shaped like every other model.
# No index=True on the PK: SQLite's autoincrement primary key is already
# unique, and an explicit second index on `id` makes the migration fail with
# "index ix_roles_id already exists" because SQLAlchemy also derives one.
_id = sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True)
_created = sa.Column(
    "created_at",
    sa.DateTime(),
    nullable=False,
    server_default=sa.func.now(),
)
_updated = sa.Column(
    "updated_at",
    sa.DateTime(),
    nullable=False,
    server_default=sa.func.now(),
)


def upgrade() -> None:
    op.create_table(
        "roles",
        _id,
        sa.Column("name", sa.String(length=64), nullable=False),
        sa.Column("description", sa.String(length=255), nullable=True),
        sa.Column("is_system", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("is_superuser", sa.Boolean(), nullable=False, server_default=sa.false()),
        _created,
        _updated,
    )
    op.create_index("ix_roles_name", "roles", ["name"], unique=True)

    op.create_table(
        "role_permissions",
        _id,
        sa.Column("role_id", sa.Integer(), nullable=False),
        sa.Column("module", sa.String(length=64), nullable=False),
        sa.Column("action", sa.String(length=16), nullable=False),
        _created,
        _updated,
        sa.ForeignKeyConstraint(["role_id"], ["roles.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("role_id", "module", "action", name="uq_role_permission"),
    )
    op.create_index("ix_role_permissions_role_id", "role_permissions", ["role_id"])
    op.create_index("ix_role_permissions_module", "role_permissions", ["module"])
    op.create_index("ix_role_permissions_action", "role_permissions", ["action"])

    # SQLite cannot ALTER a table to add a foreign key. batch_alter_table uses
    # the copy-and-move strategy, so the constraint lands correctly.
    with op.batch_alter_table("users") as batch_op:
        batch_op.add_column(sa.Column("role_id", sa.Integer(), nullable=True))
        batch_op.create_index("ix_users_role_id", ["role_id"])
        batch_op.create_foreign_key(
            "fk_users_role_id", "roles", ["role_id"], ["id"], ondelete="SET NULL"
        )


def downgrade() -> None:
    with op.batch_alter_table("users") as batch_op:
        batch_op.drop_constraint("fk_users_role_id", type_="foreignkey")
        batch_op.drop_index("ix_users_role_id")
        batch_op.drop_column("role_id")

    op.drop_index("ix_role_permissions_action", table_name="role_permissions")
    op.drop_index("ix_role_permissions_module", table_name="role_permissions")
    op.drop_index("ix_role_permissions_role_id", table_name="role_permissions")
    op.drop_table("role_permissions")

    op.drop_index("ix_roles_name", table_name="roles")
    op.drop_table("roles")
