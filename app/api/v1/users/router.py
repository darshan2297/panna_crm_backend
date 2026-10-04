
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.dependencies.auth import require_roles
from app.dependencies.database import get_db
from app.models.user import User, UserRole
from app.schemas.common import APIResponse, PaginatedResponse
from app.schemas.user import UserCreate, UserResponse, UserUpdate
from app.services.user_service import UserService

router = APIRouter(prefix="/users", tags=["User Management"])


@router.get("", response_model=PaginatedResponse[UserResponse])
def list_users(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    role: str | None = Query(None, description="Filter by role (ADMIN, MANAGER, STAFF)"),
    is_active: bool | None = Query(None, description="Filter by active status"),
    search: str | None = Query(None, description="Search by username, email, full name, or phone"),
    current_admin: User = Depends(require_roles([UserRole.ADMIN])),
    db: Session = Depends(get_db),
):
    """List system users with filtering, search, and pagination. (Admin only)"""
    service = UserService(db)
    return service.get_users(
        page=page,
        page_size=page_size,
        role=role,
        is_active=is_active,
        search=search,
    )


@router.post("", response_model=APIResponse[UserResponse], status_code=status.HTTP_201_CREATED)
def create_user(
    user_in: UserCreate,
    current_admin: User = Depends(require_roles([UserRole.ADMIN])),
    db: Session = Depends(get_db),
):
    """Create a new staff or manager user. (Admin only)"""
    service = UserService(db)
    created = service.create_user(user_in)
    return APIResponse(
        success=True,
        message=f"User '{created.username}' created successfully",
        data=created,
    )


@router.get("/{user_id}", response_model=APIResponse[UserResponse])
def get_user_details(
    user_id: int,
    current_admin: User = Depends(require_roles([UserRole.ADMIN])),
    db: Session = Depends(get_db),
):
    """Retrieve full details of a specific user. (Admin only)"""
    service = UserService(db)
    user = service.get_user_by_id(user_id)
    return APIResponse(
        success=True,
        message="User found",
        data=UserResponse.model_validate(user),
    )


@router.patch("/{user_id}", response_model=APIResponse[UserResponse])
def update_user(
    user_id: int,
    user_in: UserUpdate,
    current_admin: User = Depends(require_roles([UserRole.ADMIN])),
    db: Session = Depends(get_db),
):
    """Update a user's details, role, status, or reset password. (Admin only)"""
    service = UserService(db)
    updated = service.update_user(user_id, user_in, current_admin)
    return APIResponse(
        success=True,
        message=f"User '{updated.username}' updated successfully",
        data=updated,
    )


@router.delete("/{user_id}", response_model=APIResponse[None])
def delete_user(
    user_id: int,
    current_admin: User = Depends(require_roles([UserRole.ADMIN])),
    db: Session = Depends(get_db),
):
    """Delete a user account. Cannot delete own account. (Admin only)"""
    service = UserService(db)
    service.delete_user(user_id, current_admin)
    return APIResponse(
        success=True,
        message="User deleted successfully",
        data=None,
    )
