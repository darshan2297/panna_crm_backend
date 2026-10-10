from typing import Any

from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import ForbiddenException, UnauthorizedException
from app.core.security import decode_token
from app.dependencies.database import get_db
from app.models.user import User
from app.repositories.user_repository import UserRepository

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/login")


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    payload = decode_token(token)
    if not payload or payload.get("type") != "access":
        raise UnauthorizedException("Could not validate credentials")

    user_id = payload.get("sub")
    if not user_id:
        raise UnauthorizedException("Token missing user subject")

    user = UserRepository(db).get_by_id(int(user_id))
    if not user:
        raise UnauthorizedException("User not found")
    return user


def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    if not current_user.is_active:
        raise ForbiddenException("Inactive user account")
    return current_user


def require_roles(allowed_roles: list[Any]):
    def role_checker(current_user: User = Depends(get_current_active_user)) -> User:
        allowed_values = [r.value if hasattr(r, "value") else str(r) for r in allowed_roles]
        if current_user.role not in allowed_values:
            raise ForbiddenException(f"Role '{current_user.role}' does not have required permissions")
        return current_user

    return role_checker


def require_permission(module: str, action: str):
    """Enforce a module/action grant on the current user's role.

    Usage:
        @router.post("/items")
        def create(..., _: User = Depends(require_permission("INVENTORY", "CREATE")))

    Kept as a factory so the grant is declared next to the route it protects,
    which is where a reviewer will look for it.
    """
    from app.models.role import Module, PermissionAction

    module_value = module.value if hasattr(module, "value") else str(module)
    action_value = action.value if hasattr(action, "value") else str(action)
    assert module_value in {m.value for m in Module}, f"Unknown module '{module_value}'"
    assert action_value in {a.value for a in PermissionAction}, f"Unknown action '{action_value}'"

    def permission_checker(current_user: User = Depends(get_current_active_user)) -> User:
        if not current_user.has_permission(module_value, action_value):
            raise ForbiddenException(
                message=f"You do not have '{action_value}' permission on '{module_value}'"
            )
        return current_user

    return permission_checker
