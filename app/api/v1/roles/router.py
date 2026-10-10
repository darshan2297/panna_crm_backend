from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.dependencies.auth import require_roles
from app.dependencies.database import get_db
from app.models.user import User, UserRole
from app.schemas.common import APIResponse
from app.schemas.role import (
    PermissionMatrixResponse,
    RoleCreate,
    RoleResponse,
    RoleUpdate,
)
from app.services.role_service import RoleService

router = APIRouter(prefix="/roles", tags=["Roles & Permissions"])

# Every role-management route is admin-only. Note this checks the legacy role
# column rather than a permission grant: managing who holds which permission is
# the one action that must not itself be grantable away, or an admin could
# remove their own access with no way back through the UI.
_admin_only = Depends(require_roles([UserRole.ADMIN]))


@router.get("", response_model=APIResponse[list[RoleResponse]])
def list_roles(
    current_admin: User = _admin_only,
    db: Session = Depends(get_db),
):
    """List all roles with their permission grants and user counts. (Admin only)"""
    service = RoleService(db)
    return APIResponse(
        success=True,
        message="Roles retrieved successfully",
        data=service.get_roles(),
    )


@router.get("/matrix", response_model=APIResponse[PermissionMatrixResponse])
def get_permission_matrix(
    current_admin: User = _admin_only,
    db: Session = Depends(get_db),
):
    """Return the module catalogue plus every role, for the roles editor UI."""
    service = RoleService(db)
    return APIResponse(
        success=True,
        message="Permission matrix retrieved successfully",
        data=service.get_matrix(),
    )


@router.get("/{role_id}", response_model=APIResponse[RoleResponse])
def get_role(
    role_id: int,
    current_admin: User = _admin_only,
    db: Session = Depends(get_db),
):
    """Retrieve a single role with its grants. (Admin only)"""
    service = RoleService(db)
    role = service.get_role(role_id)
    return APIResponse(
        success=True,
        message="Role retrieved successfully",
        data=RoleResponse.model_validate(role),
    )


@router.post("", response_model=APIResponse[RoleResponse], status_code=status.HTTP_201_CREATED)
def create_role(
    role_in: RoleCreate,
    current_admin: User = _admin_only,
    db: Session = Depends(get_db),
):
    """Create a new role with the given permission grants. (Admin only)"""
    service = RoleService(db)
    created = service.create_role(role_in, current_admin)
    return APIResponse(
        success=True,
        message=f"Role '{created.name}' created successfully",
        data=created,
    )


@router.patch("/{role_id}", response_model=APIResponse[RoleResponse])
def update_role(
    role_id: int,
    role_in: RoleUpdate,
    current_admin: User = _admin_only,
    db: Session = Depends(get_db),
):
    """Rename a role or replace its permission grants. (Admin only)"""
    service = RoleService(db)
    updated = service.update_role(role_id, role_in, current_admin)
    return APIResponse(
        success=True,
        message=f"Role '{updated.name}' updated successfully",
        data=updated,
    )


@router.delete("/{role_id}", response_model=APIResponse[None])
def delete_role(
    role_id: int,
    current_admin: User = _admin_only,
    db: Session = Depends(get_db),
):
    """Delete a custom role. System and superuser roles cannot be deleted."""
    service = RoleService(db)
    service.delete_role(role_id, current_admin)
    return APIResponse(
        success=True,
        message="Role deleted successfully",
        data=None,
    )
