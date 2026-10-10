"""Role-based access control.

Replaces the flat `users.role` string (ADMIN/MANAGER/STAFF) with a real role
table plus a module/action permission matrix, so access is configurable per role
rather than hard-coded to a fixed ladder of tiers.

  roles             named, editable bundles of permissions
  role_permissions  the grants themselves (role_id, module, action)
  users.role_id     FK to roles

ADMIN is deliberately *not* special-cased in the permission tables: it holds an
explicit grant for every module/action. That keeps one code path for
authorisation and means an admin can be demoted by editing its role like any
other. `is_superuser` is the only escape hatch, and it exists for recovery when
every role has been stripped of access.
"""

import enum

from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.models.base import TimestampMixin


class PermissionAction(str, enum.Enum):
    """Actions a role can hold on a module.

    VIEW covers reading lists and detail screens. CREATE/UPDATE/DELETE are the
    write actions. Settings modules have no records, so a single UPDATE grant
    (change configuration) is what their editor needs.
    """

    VIEW = "VIEW"
    CREATE = "CREATE"
    UPDATE = "UPDATE"
    DELETE = "DELETE"


class Module(str, enum.Enum):
    """Every permissioned area of the CRM.

    Keyed to the sidebar so the UI can hide what the caller cannot reach. Order
    is the display order of the roles matrix.
    """

    DASHBOARD = "DASHBOARD"
    ORDERS = "ORDERS"
    LIVE_ORDERS = "LIVE_ORDERS"
    CUSTOMERS = "CUSTOMERS"
    ENQUIRIES = "ENQUIRIES"
    STAFF = "STAFF"
    ROLES = "ROLES"
    MENU = "MENU"
    INVENTORY = "INVENTORY"
    PACKAGING = "PACKAGING"
    RESTOCK = "RESTOCK"
    ANALYTICS = "ANALYTICS"
    INTEGRATIONS = "INTEGRATIONS"
    BUSINESS_HOURS = "BUSINESS_HOURS"
    WEBSITE_CONFIG = "WEBSITE_CONFIG"
    PROMO_CODES = "PROMO_CODES"
    DELIVERY_AREAS = "DELIVERY_AREAS"
    REVIEWS = "REVIEWS"
    FAQS = "FAQS"
    SETTINGS = "SETTINGS"


class Role(Base, TimestampMixin):
    __tablename__ = "roles"

    name = Column(String(64), unique=True, nullable=False, index=True)
    description = Column(String(255), nullable=True)
    # System roles are seeded on startup and cannot be deleted or renamed.
    # Their permissions are still editable.
    is_system = Column(Boolean, default=False, nullable=False)
    # Bypasses every permission check. Reserved for lockout recovery.
    is_superuser = Column(Boolean, default=False, nullable=False)

    permissions = relationship(
        "RolePermission",
        back_populates="role",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    users = relationship("User", back_populates="role_rel")

    def __repr__(self) -> str:
        return f"<Role {self.name}>"


class RolePermission(Base, TimestampMixin):
    __tablename__ = "role_permissions"
    __table_args__ = (
        UniqueConstraint("role_id", "module", "action", name="uq_role_permission"),
    )

    role_id = Column(
        Integer,
        ForeignKey("roles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    module = Column(String(64), nullable=False, index=True)
    action = Column(String(16), nullable=False, index=True)

    role = relationship("Role", back_populates="permissions")

    def __repr__(self) -> str:
        return f"<RolePermission {self.module}:{self.action}>"
