"""Role and permission management. Every route is admin-only."""

from sqlalchemy.orm import Session

from app.core.exceptions import AppException, NotFoundException
from app.models.role import Module, PermissionAction, Role, RolePermission
from app.models.user import User
from app.schemas.role import (
    ModuleInfo,
    PermissionGrant,
    PermissionMatrixResponse,
    RoleCreate,
    RoleResponse,
    RoleUpdate,
)
from app.services.permission_catalogue import (
    LEGACY_ROLE_TO_ROLE_NAME,
    MODULE_CATALOGUE,
    build_role_object,
)


class RoleService:
    def __init__(self, db: Session):
        self.db = db

    # ------------------------------------------------------------------ #
    # seeding
    # ------------------------------------------------------------------ #
    def seed_default_roles(self) -> None:
        """Create the default roles and attach unassigned users.

        Idempotent: existing roles keep whatever an admin has configured, so
        restarts never silently revert permission edits. Only the role_id
        backfill runs every time, for users created before the migration.
        """
        for spec in _DEFAULT_ROLE_SPECS:
            existing = self.db.query(Role).filter_by(name=spec["name"]).first()
            if existing is None:
                role = build_role_object(spec)
                self.db.add(role)
                self.db.flush()
                self.db.refresh(role)
                self.db.commit()

        # Backfill role_id from the legacy column for any unassigned user.
        for user in self.db.query(User).filter(User.role_id.is_(None)).all():
            role_name = LEGACY_ROLE_TO_ROLE_NAME.get(user.role)
            if not role_name:
                continue
            role = self.db.query(Role).filter_by(name=role_name).first()
            if role:
                user.role_id = role.id
        self.db.commit()

    # ------------------------------------------------------------------ #
    # reads
    # ------------------------------------------------------------------ #
    def get_roles(self) -> list[RoleResponse]:
        roles = self.db.query(Role).order_by(Role.is_superuser.desc(), Role.name).all()
        out = []
        for r in roles:
            resp = RoleResponse.model_validate(r)
            resp.user_count = (
                self.db.query(User).filter(User.role_id == r.id).count()
            )
            out.append(resp)
        return out

    def get_matrix(self) -> PermissionMatrixResponse:
        return PermissionMatrixResponse(
            modules=[
                ModuleInfo(module=m, label=label, actions=actions)
                for m, label, actions in MODULE_CATALOGUE
            ],
            roles=self.get_roles(),
        )

    def get_role(self, role_id: int) -> Role:
        role = self.db.query(Role).filter_by(id=role_id).first()
        if not role:
            raise NotFoundException("Role", role_id)
        return role

    # ------------------------------------------------------------------ #
    # writes
    # ------------------------------------------------------------------ #
    def create_role(self, payload: RoleCreate, actor: User) -> RoleResponse:
        if self.db.query(Role).filter_by(name=payload.name.strip()).first():
            raise AppException(message=f"Role '{payload.name}' already exists")

        role = Role(
            name=payload.name.strip(),
            description=payload.description,
            is_system=False,
            is_superuser=False,
        )
        self._set_permissions(role, payload.permissions)
        self.db.add(role)
        self.db.commit()
        self.db.refresh(role)
        return RoleResponse.model_validate(role)

    def update_role(self, role_id: int, payload: RoleUpdate, actor: User) -> RoleResponse:
        role = self.get_role(role_id)

        if role.is_system and payload.name and payload.name.strip() != role.name:
            raise AppException(message="System role names cannot be changed")

        if payload.name is not None and not role.is_system:
            clash = (
                self.db.query(Role)
                .filter(Role.name == payload.name.strip(), Role.id != role_id)
                .first()
            )
            if clash:
                raise AppException(message=f"Role '{payload.name}' already exists")
            role.name = payload.name.strip()

        if payload.description is not None:
            role.description = payload.description

        if payload.permissions is not None:
            self._assert_not_last_admin(role, payload.permissions)
            # Replace, never merge. Simply assigning to role.permissions leaves
            # the existing rows live in the session, so re-granting a permission
            # the role already holds INSERTs a duplicate and trips the
            # (role_id, module, action) unique constraint.
            #
            # synchronize_session="fetch" makes the session forget the deleted
            # rows, and expiring the relationship stops the ORM from diffing
            # against the stale collection.
            self.db.query(RolePermission).filter_by(role_id=role.id).delete(
                synchronize_session="fetch"
            )
            self.db.flush()
            self.db.expire(role, ["permissions"])
            self._set_permissions(role, payload.permissions)

        self.db.commit()
        self.db.refresh(role)
        return RoleResponse.model_validate(role)

    def delete_role(self, role_id: int, actor: User) -> None:
        role = self.get_role(role_id)
        if role.is_system:
            raise AppException(message="System roles cannot be deleted")
        if role.is_superuser:
            raise AppException(message="Superuser roles cannot be deleted")

        in_use = self.db.query(User).filter(User.role_id == role_id).count()
        if in_use:
            raise AppException(
                message=f"Cannot delete '{role.name}': {in_use} user(s) still assigned. "
                "Reassign them first."
            )
        self.db.delete(role)
        self.db.commit()

    # ------------------------------------------------------------------ #
    # internals
    # ------------------------------------------------------------------ #
    def _set_permissions(self, role: Role, grants: list[PermissionGrant]) -> None:
        supported = {
            m: set(a.value for a in actions) for m, _, actions in MODULE_CATALOGUE
        }
        wanted: set[tuple[str, str]] = set()
        for g in grants:
            allowed = supported.get(g.module, set())
            if g.action.value not in allowed:
                raise AppException(
                    message=f"Action '{g.action.value}' is not valid for module "
                    f"'{g.module.value}'"
                )
            wanted.add((g.module.value, g.action.value))

        role.permissions = [
            RolePermission(module=m, action=a) for m, a in sorted(wanted)
        ]

    def _assert_not_last_admin(self, role: Role, grants: list[PermissionGrant]) -> None:
        """Refuse a change that would leave nobody able to administer roles.

        The real risk is not "this role loses ROLES" but "no active user anywhere
        can still reach ROLES afterwards" — the system then has no UI route back
        and would need a direct database edit. So this checks the whole
        population, not just the holders of the role being edited.

        A superuser role bypasses every check, so trimming its grants cannot
        actually revoke access and is never blocked.
        """
        # Still granted, or the role itself cannot revoke anything.
        if role.is_superuser:
            return
        if any(g.module == Module.ROLES and g.action == PermissionAction.VIEW for g in grants):
            return

        # Anyone else on a superuser role can still administer regardless.
        survivors = 0
        for holder in (
            self.db.query(User).filter(User.is_active.is_(True)).all()
        ):
            holder_role = holder.role_rel
            if holder_role is None:
                # Legacy account with no role: falls back to the old ladder.
                if holder.role == "ADMIN":
                    survivors += 1
                continue
            if holder_role.is_superuser:
                survivors += 1
                continue
            if holder_role.id == role.id:
                continue  # the role being stripped right now
            if any(
                p.module == Module.ROLES.value and p.action == PermissionAction.VIEW.value
                for p in holder_role.permissions
            ):
                survivors += 1

        if survivors == 0:
            raise AppException(
                message="Cannot remove role-management access from the only remaining "
                "administrator. Grant ROLES to another role, or add another "
                "administrator, first."
            )


# Imported late to avoid a circular import with the service module.
from app.services.permission_catalogue import DEFAULT_ROLES as _DEFAULT_ROLE_SPECS  # noqa: E402
