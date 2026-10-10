from sqlalchemy.orm import Session

from app.core.exceptions import (
    ConflictException,
    ForbiddenException,
    NotFoundException,
    UnauthorizedException,
)
from app.core.security import get_password_hash, verify_password
from app.models.user import User, UserRole
from app.repositories.user_repository import UserRepository
from app.schemas.auth import ChangePasswordRequest, UpdateProfileRequest
from app.schemas.common import PaginatedResponse
from app.schemas.user import UserCreate, UserResponse, UserUpdate
from app.utils.pagination import calc_pages


class UserService:
    def __init__(self, db: Session):
        self.db = db
        self.user_repo = UserRepository(db)

    def get_users(
        self,
        page: int = 1,
        page_size: int = 20,
        role: str | None = None,
        is_active: bool | None = None,
        search: str | None = None,
    ) -> PaginatedResponse[UserResponse]:
        skip = (page - 1) * page_size
        items, total = self.user_repo.get_filtered_users(
            skip=skip,
            limit=page_size,
            role=role,
            is_active=is_active,
            search=search,
        )
        pages = calc_pages(total, page_size)

        return PaginatedResponse(
            total=total,
            page=page,
            page_size=page_size,
            pages=pages,
            items=[UserResponse.model_validate(u) for u in items],
        )

    def get_user_by_id(self, user_id: int) -> User:
        user = self.user_repo.get_by_id(user_id)
        if not user:
            raise NotFoundException("User", user_id)
        return user

    def create_user(self, user_in: UserCreate) -> UserResponse:
        # Check email duplicate
        if self.user_repo.get_by_email(user_in.email):
            raise ConflictException(f"User with email '{user_in.email}' already exists")

        # Check username duplicate
        if self.user_repo.get_by_username(user_in.username):
            raise ConflictException(f"Username '{user_in.username}' is already taken")

        role_id = self._resolve_role_id(user_in.role_id, user_in.role)

        # The legacy column backs require_roles() and the JWT, so it
        # must follow the assigned role. Unmapped (custom) role names
        # are written through as-is: they match no UserRole value,
        # which is exactly what we want — a custom role is never an
        # implicit administrator.
        legacy_role = (
            user_in.role.value if isinstance(user_in.role, UserRole) else str(user_in.role)
        )
        if user_in.role_id is not None and role_id is not None:
            from app.models.role import Role
            from app.services.permission_catalogue import LEGACY_ROLE_TO_ROLE_NAME

            role_row = self.db.query(Role).filter_by(id=role_id).first()
            if role_row is not None:
                # The legacy column only ever holds ADMIN/MANAGER/STAFF
                # (UserResponse validates it as an enum), so a custom role
                # falls back to the most restrictive value. That keeps a
                # stale ADMIN from surviving a reassignment.
                legacy_role = LEGACY_ROLE_TO_ROLE_NAME.get(role_row.name, "STAFF")

        new_user = User(
            email=user_in.email,
            username=user_in.username,
            full_name=user_in.full_name,
            phone=user_in.phone,
            hashed_password=get_password_hash(user_in.password),
            role=legacy_role,
            role_id=role_id,
            is_active=user_in.is_active,
        )
        created = self.user_repo.create(new_user)
        return UserResponse.model_validate(created)

    def _resolve_role_id(self, role_id: int | None, legacy_role: object = None) -> int | None:
        """Map an explicit role_id, or a legacy role value, onto a Role row.

        Keeping `users.role` in sync matters because the JWT carries it and
        require_roles() still reads it, so the two must not drift.
        """
        from app.models.role import Role
        from app.services.permission_catalogue import LEGACY_ROLE_TO_ROLE_NAME

        if role_id is not None:
            role = self.db.query(Role).filter_by(id=role_id).first()
            if not role:
                raise NotFoundException("Role", role_id)
            return role.id

        legacy_value = (
            legacy_role.value if hasattr(legacy_role, "value") else str(legacy_role or "")
        )
        name = LEGACY_ROLE_TO_ROLE_NAME.get(legacy_value)
        if name:
            role = self.db.query(Role).filter_by(name=name).first()
            if role:
                return role.id
        return None

    def update_user(self, user_id: int, user_in: UserUpdate, current_admin: User) -> UserResponse:
        user = self.get_user_by_id(user_id)

        # Check email change uniqueness
        if user_in.email and user_in.email != user.email:
            existing = self.user_repo.get_by_email(user_in.email)
            if existing and existing.id != user.id:
                raise ConflictException(f"Email '{user_in.email}' is already in use")
            user.email = user_in.email

        if user_in.full_name is not None:
            user.full_name = user_in.full_name

        if user_in.phone is not None:
            user.phone = user_in.phone

        if user_in.role_id is not None:
            if user.id == current_admin.id:
                raise ForbiddenException("You cannot change your own role")
            user.role_id = self._resolve_role_id(user_in.role_id)
            # Keep the legacy column aligned so require_roles() and the JWT agree.
            # A custom role name maps to no legacy value, so it falls back to
            # STAFF — never a stale ADMIN left behind by a reassignment.
            if user.role_rel is not None:
                from app.services.permission_catalogue import LEGACY_ROLE_TO_ROLE_NAME

                user.role = LEGACY_ROLE_TO_ROLE_NAME.get(user.role_rel.name, "STAFF")

        if user_in.role is not None:
            # Prevent demoting the only admin if self
            if user.id == current_admin.id and user_in.role != UserRole.ADMIN:
                raise ForbiddenException("You cannot change your own admin role")
            user.role = user_in.role.value if isinstance(user_in.role, UserRole) else str(user_in.role)
            if user_in.role_id is None:
                user.role_id = self._resolve_role_id(None, user_in.role)

        if user_in.is_active is not None:
            # Prevent deactivating yourself
            if user.id == current_admin.id and not user_in.is_active:
                raise ForbiddenException("You cannot deactivate your own account")
            user.is_active = user_in.is_active

        if user_in.password:
            user.hashed_password = get_password_hash(user_in.password)

        updated = self.user_repo.update(user)
        return UserResponse.model_validate(updated)

    def delete_user(self, user_id: int, current_admin: User) -> None:
        user = self.get_user_by_id(user_id)
        if user.id == current_admin.id:
            raise ForbiddenException("You cannot delete your own account")
        self.user_repo.delete(user)

    def change_password(self, user_id: int, req: ChangePasswordRequest) -> None:
        user = self.get_user_by_id(user_id)
        if not verify_password(req.old_password, user.hashed_password):
            raise UnauthorizedException("Incorrect current password")
        user.hashed_password = get_password_hash(req.new_password)
        self.user_repo.update(user)

    def update_profile(self, user_id: int, req: UpdateProfileRequest) -> UserResponse:
        user = self.get_user_by_id(user_id)

        if req.email and req.email != user.email:
            existing = self.user_repo.get_by_email(req.email)
            if existing and existing.id != user.id:
                raise ConflictException(f"Email '{req.email}' is already registered")
            user.email = req.email

        if req.full_name is not None:
            user.full_name = req.full_name

        if req.phone is not None:
            user.phone = req.phone

        updated = self.user_repo.update(user)
        return UserResponse.model_validate(updated)
