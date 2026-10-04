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
