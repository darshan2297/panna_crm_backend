from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundException
from app.dependencies.auth import get_current_active_user, require_permission
from app.dependencies.database import get_db
from app.models.user import User
from app.schemas.common import APIResponse, PaginatedResponse
from app.schemas.notification import (
    NotificationDispatchInput,
    NotificationDispatchResult,
    NotificationOut,
    NotificationSummary,
)
from app.services.notification_service import NotificationService
from app.utils.pagination import calc_pages

router = APIRouter(prefix="/notifications", tags=["Notifications & Alerts"])


@router.get("", response_model=APIResponse[PaginatedResponse[NotificationOut]])
def list_notifications(
    is_read: bool | None = Query(None, description="Filter by read status"),
    type: str | None = Query(None, description="Filter by notification type"),
    severity: str | None = Query(None, description="Filter by severity (INFO, WARNING, CRITICAL, SUCCESS)"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("DASHBOARD", "VIEW")),
):
    """Retrieve notifications with pagination, read filter, type, and severity."""
    offset = (page - 1) * page_size
    total, items = NotificationService.list_notifications(
        db=db,
        is_read=is_read,
        ntype=type,
        severity=severity,
        limit=page_size,
        offset=offset,
    )
    pages = calc_pages(total, page_size)

    return APIResponse(
        success=True,
        message="Notifications retrieved successfully",
        data=PaginatedResponse(
            total=total,
            page=page,
            page_size=page_size,
            pages=pages,
            items=[NotificationOut.model_validate(n) for n in items],
        ),
    )


@router.get("/unread-count", response_model=APIResponse[dict])
def get_unread_count(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("DASHBOARD", "VIEW")),
):
    """Get fast count of unread notifications for badge indicator."""
    count = NotificationService.get_unread_count(db)
    return APIResponse(
        success=True,
        message="Unread count retrieved",
        data={"unread_count": count},
    )


@router.get("/summary", response_model=APIResponse[NotificationSummary])
def get_notification_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("DASHBOARD", "VIEW")),
):
    """Get breakdown summary of alerts (critical, warnings, stock breaches)."""
    summary = NotificationService.get_summary(db)
    return APIResponse(
        success=True,
        message="Notification summary retrieved",
        data=summary,
    )


@router.patch("/{id}/read", response_model=APIResponse[NotificationOut])
def mark_notification_as_read(
    id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("DASHBOARD", "VIEW")),
):
    """Mark a notification as read."""
    notif = NotificationService.mark_as_read(db, id)
    if not notif:
        raise NotFoundException("Notification")
    return APIResponse(
        success=True,
        message="Notification marked as read",
        data=NotificationOut.model_validate(notif),
    )


@router.post("/mark-all-read", response_model=APIResponse[dict])
def mark_all_notifications_as_read(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Mark all unread notifications as read in a single click."""
    count = NotificationService.mark_all_as_read(db)
    return APIResponse(
        success=True,
        message=f"{count} notifications marked as read",
        data={"updated_count": count},
    )


@router.delete("/{id}", response_model=APIResponse[dict])
def delete_notification(
    id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Delete a notification."""
    success = NotificationService.delete_notification(db, id)
    if not success:
        raise NotFoundException("Notification")
    return APIResponse(
        success=True,
        message="Notification deleted successfully",
        data={"deleted_id": id},
    )


@router.post("/scan", response_model=APIResponse[dict])
def scan_kitchen_stock_alerts(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """On-demand scan of inventory ingredients and packaging stock for safety breaches."""
    count, notifs = NotificationService.scan_and_generate_stock_alerts(db)
    return APIResponse(
        success=True,
        message=f"Stock scan completed: {count} new alert(s) generated",
        data={"alerts_generated": count},
    )


@router.post("/{id}/dispatch", response_model=APIResponse[NotificationDispatchResult])
def dispatch_notification_alert(
    id: int,
    payload: NotificationDispatchInput,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Dispatch an alert externally via WhatsApp or Email."""
    res = NotificationService.dispatch_notification(
        db=db,
        notification_id=id,
        channel=payload.channel,
        recipient=payload.recipient,
        custom_message=payload.custom_message,
    )
    return APIResponse(
        success=True,
        message=f"Alert dispatched via {payload.channel}",
        data=res,
    )
