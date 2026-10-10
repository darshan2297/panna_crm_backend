import enum

from sqlalchemy import Boolean, Column, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.models.base import TimestampMixin
from app.models.role import Role


class UserRole(str, enum.Enum):
    """Legacy role values, retained so existing tokens and rows keep working.

    Access is no longer decided by this field — it maps to a Role row via
    `users.role_id`. It is kept in sync on write for backward compatibility and
    for the JWT's `role` claim.
    """

    ADMIN = "ADMIN"
    MANAGER = "MANAGER"
    STAFF = "STAFF"


class User(Base, TimestampMixin):
    __tablename__ = "users"

    email = Column(String(255), unique=True, index=True, nullable=False)
    username = Column(String(100), unique=True, index=True, nullable=False)
    full_name = Column(String(255), nullable=False)
    phone = Column(String(50), nullable=True)
    hashed_password = Column(String(255), nullable=False)
    role = Column(String(50), default=UserRole.STAFF.value, nullable=False)
    role_id = Column(Integer, ForeignKey("roles.id", ondelete="SET NULL"), nullable=True, index=True)
    is_active = Column(Boolean, default=True, nullable=False)

    role_rel = relationship("Role", lazy="selectin")

    def __repr__(self) -> str:
        return f"<User {self.username} ({self.role})>"

    # --- permission helpers -------------------------------------------- #
    def has_permission(self, module: str, action: str) -> bool:
        """Whether this user may perform `action` on `module`.

        A missing Role (not yet assigned, or a pre-RBAC account) resolves to the
        legacy `role` column so existing users are never locked out by the
        migration.
        """
        role = self.role_rel
        if role is not None:
            if role.is_superuser:
                return True
            return any(
                p.module == module and p.action == action for p in role.permissions
            )

        # Fallback for users with no role_id assigned.
        if self.role == UserRole.ADMIN.value:
            return True
        if action == "VIEW" and self.role in (UserRole.MANAGER.value, UserRole.STAFF.value):
            return True
        return False
