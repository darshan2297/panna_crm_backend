from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import AppException, UnauthorizedException
from app.core.logging import logger
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    get_password_hash,
    verify_password,
)
from app.models.user import User, UserRole
from app.repositories.user_repository import UserRepository
from app.schemas.auth import TokenResponse


class AuthService:
    def __init__(self, db: Session):
        self.db = db
        self.user_repo = UserRepository(db)

    def authenticate_user(self, identifier: str, password: str) -> User | None:
        user = self.user_repo.get_by_username_or_email(identifier)
        if not user:
            return None
        if not verify_password(password, user.hashed_password):
            return None
        return user

    def login(self, identifier: str, password: str) -> TokenResponse:
        user = self.authenticate_user(identifier, password)
        if not user:
            raise UnauthorizedException("Incorrect username/email or password")
        if not user.is_active:
            raise AppException(message="Account is deactivated. Contact administrator.")

        access_token = create_access_token(subject=str(user.id), role=user.role)
        refresh_token = create_refresh_token(subject=str(user.id))

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        )

    def refresh(self, refresh_token: str) -> TokenResponse:
        payload = decode_token(refresh_token)
        if not payload or payload.get("type") != "refresh":
            raise UnauthorizedException("Invalid or expired refresh token")

        user_id = payload.get("sub")
        if not user_id:
            raise UnauthorizedException("Invalid token subject")

        user = self.user_repo.get_by_id(int(user_id))
        if not user or not user.is_active:
            raise UnauthorizedException("User not found or inactive")

        new_access_token = create_access_token(subject=str(user.id), role=user.role)
        new_refresh_token = create_refresh_token(subject=str(user.id))

        return TokenResponse(
            access_token=new_access_token,
            refresh_token=new_refresh_token,
            token_type="bearer",
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        )

    def init_default_users(self) -> None:
        """Seed initial Admin, Manager, and Staff accounts for immediate testing."""
        # Roles are seeded by RoleService.seed_default_roles() during startup,
        # which runs before this. Resolve by name so each account is linked to
        # its role row rather than leaving role_id null.
        from app.models.role import Role

        roles_by_name = {r.name: r for r in self.db.query(Role).all()}

        default_accounts = [
            {
                "username": "admin",
                "email": "admin@pannabiryani.com",
                "full_name": "Panna Master Admin",
                "phone": "+91 9876543210",
                "password": "admin123",
                "role": UserRole.ADMIN.value,
            },
            {
                "username": "manager",
                "email": "manager@pannabiryani.com",
                "full_name": "Panna Kitchen Manager",
                "phone": "+91 9876543211",
                "password": "manager123",
                "role": UserRole.MANAGER.value,
            },
            {
                "username": "staff",
                "email": "staff@pannabiryani.com",
                "full_name": "Panna Kitchen Staff",
                "phone": "+91 9876543212",
                "password": "staff123",
                "role": UserRole.STAFF.value,
            },
        ]

        from app.services.permission_catalogue import LEGACY_ROLE_TO_ROLE_NAME

        for acc in default_accounts:
            role_name = LEGACY_ROLE_TO_ROLE_NAME.get(acc["role"], "Staff")
            role = roles_by_name.get(role_name)
            existing = self.user_repo.get_by_username(acc["username"])
            if not existing:
                u = User(
                    email=acc["email"],
                    username=acc["username"],
                    full_name=acc["full_name"],
                    phone=acc["phone"],
                    hashed_password=get_password_hash(acc["password"]),
                    role=acc["role"],
                    role_id=role.id if role else None,
                    is_active=True,
                )
                self.user_repo.create(u)
                logger.info(f"Initialized default user: {acc['username']} ({acc['role']})")
            elif existing.role_id is None and role:
                # Pre-RBAC account: link it to its role so it gets real grants.
                existing.role_id = role.id
                self.db.commit()

    # Retain backward-compatible method name for lifespan
    def init_default_admin(self) -> None:
        self.init_default_users()
