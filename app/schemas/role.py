from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.role import Module, PermissionAction


class PermissionGrant(BaseModel):
    """A single module/action grant on a role."""

    module: Module
    action: PermissionAction

    # RolePermission ORM rows are validated straight into this schema, so the
    # attribute mapping is required — without it Pydantic rejects them as
    # "not a valid PermissionGrant".
    model_config = ConfigDict(from_attributes=True)


class RoleBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=64)
    description: str | None = Field(None, max_length=255)


class RoleCreate(RoleBase):
    permissions: list[PermissionGrant] = []


class RoleUpdate(BaseModel):
    name: str | None = Field(None, min_length=2, max_length=64)
    description: str | None = Field(None, max_length=255)
    permissions: list[PermissionGrant] | None = None


class RoleResponse(RoleBase):
    id: int
    is_system: bool
    is_superuser: bool
    permissions: list[PermissionGrant] = []
    user_count: int = 0
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ModuleInfo(BaseModel):
    """One row of the roles matrix in the UI."""

    module: Module
    label: str
    actions: list[PermissionAction]


class PermissionMatrixResponse(BaseModel):
    """Everything the roles editor needs in one request."""

    modules: list[ModuleInfo]
    roles: list[RoleResponse]


class UserPermissionResponse(BaseModel):
    """The caller's own effective permissions, for frontend gating."""

    role: str | None = None
    role_id: int | None = None
    is_superuser: bool = False
    permissions: list[str] = []
