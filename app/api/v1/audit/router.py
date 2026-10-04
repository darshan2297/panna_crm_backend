
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.dependencies.auth import require_roles
from app.dependencies.database import get_db
from app.models.user import User, UserRole
from app.schemas.audit import AuditLogRead, AuditStats
from app.schemas.common import APIResponse, PaginatedResponse
from app.services.audit_service import AuditService
from app.utils.pagination import calc_pages

router = APIRouter(prefix="/audit", tags=["Audit & Security"])


@router.get("/logs", response_model=PaginatedResponse[AuditLogRead])
def list_audit_logs(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    action: str | None = Query(None, description="Action filter: ALL, CREATE, UPDATE, DELETE, STATUS_CHANGE, SYNC, EXPORT"),
    entity_type: str | None = Query(None, description="Entity type: ALL, ORDER, INVENTORY, PACKAGING, CUSTOMER, STAFF, MENU, SETTINGS, INTEGRATION"),
    search: str | None = Query(None, description="Free text search in details or entity ID"),
    user_email: str | None = Query(None),
    current_user: User = Depends(require_roles([UserRole.ADMIN.value, UserRole.MANAGER.value])),
    db: Session = Depends(get_db),
):
    service = AuditService(db)
    logs, total = service.get_logs(
        page=page,
        page_size=page_size,
        action=action,
        entity_type=entity_type,
        search=search,
        user_email=user_email,
    )
    pages = calc_pages(total, page_size)

    return PaginatedResponse(
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
        items=logs,
    )


@router.get("/stats", response_model=APIResponse[AuditStats])
def get_audit_stats(
    current_user: User = Depends(require_roles([UserRole.ADMIN.value, UserRole.MANAGER.value])),
    db: Session = Depends(get_db),
):
    service = AuditService(db)
    stats = service.get_stats()
    return APIResponse(success=True, message="Audit statistics retrieved", data=stats)
