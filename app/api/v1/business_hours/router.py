from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.dependencies.auth import get_current_active_user, require_roles
from app.dependencies.database import get_db
from app.models.user import User, UserRole
from app.schemas.business_hours import (
    BusinessHolidayCreate,
    BusinessHolidayRead,
    BusinessHolidayUpdate,
    BusinessHourDayRead,
    BusinessHourDayUpdate,
    BusinessHoursConfigRead,
    BusinessHoursConfigUpdate,
    BusinessHoursRead,
)
from app.schemas.common import APIResponse
from app.services.audit_service import record_audit
from app.services.business_hours_service import BusinessHoursService

router = APIRouter(prefix="/business-hours", tags=["Business Hours & Holidays"])


@router.get("", response_model=APIResponse[BusinessHoursRead])
def get_business_hours(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Retrieve weekly operating schedule, holiday calendar and global config."""
    service = BusinessHoursService(db)
    return APIResponse(success=True, message="Business hours retrieved", data=service.get_full())


@router.patch("/config", response_model=APIResponse[BusinessHoursConfigRead])
def update_business_hours_config(
    payload: BusinessHoursConfigUpdate,
    current_user: User = Depends(require_roles([UserRole.ADMIN.value, UserRole.MANAGER.value])),
    db: Session = Depends(get_db),
):
    """Enable/disable the automatic schedule and configure timezone/message."""
    service = BusinessHoursService(db)
    config = service.update_config(payload)
    record_audit(
        db=db,
        action="UPDATE",
        entity_type="BUSINESS_HOURS",
        entity_id="CONFIG",
        details="Updated business hours global configuration",
        user_email=current_user.email,
        user_id=current_user.id,
    )
    return APIResponse(success=True, message="Business hours configuration saved", data=config)


@router.patch("/days/{day_of_week}", response_model=APIResponse[BusinessHourDayRead])
def update_business_hour_day(
    day_of_week: int,
    payload: BusinessHourDayUpdate,
    current_user: User = Depends(require_roles([UserRole.ADMIN.value, UserRole.MANAGER.value])),
    db: Session = Depends(get_db),
):
    """Update a weekday's opening hours. day_of_week: 0=Monday .. 6=Sunday."""
    service = BusinessHoursService(db)
    day = service.update_day(day_of_week, payload)
    record_audit(
        db=db,
        action="UPDATE",
        entity_type="BUSINESS_HOURS",
        entity_id=f"DAY_{day_of_week}",
        details=f"Updated hours for {day.day_name}",
        user_email=current_user.email,
        user_id=current_user.id,
    )
    return APIResponse(success=True, message=f"{day.day_name} hours saved", data=day)


@router.get("/holidays", response_model=APIResponse[list[BusinessHolidayRead]])
def list_holidays(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    service = BusinessHoursService(db)
    return APIResponse(success=True, message="Holidays retrieved", data=service.get_holidays())


@router.post("/holidays", response_model=APIResponse[BusinessHolidayRead])
def create_holiday(
    payload: BusinessHolidayCreate,
    current_user: User = Depends(require_roles([UserRole.ADMIN.value, UserRole.MANAGER.value])),
    db: Session = Depends(get_db),
):
    """Add or replace a holiday / date-specific hours override."""
    service = BusinessHoursService(db)
    holiday = service.create_or_update_holiday(payload)
    record_audit(
        db=db,
        action="CREATE",
        entity_type="BUSINESS_HOURS",
        entity_id=str(holiday.holiday_date),
        details=f"Holiday/override set for {holiday.holiday_date} (closed={holiday.is_closed})",
        user_email=current_user.email,
        user_id=current_user.id,
    )
    return APIResponse(success=True, message="Holiday saved", data=holiday)


@router.patch("/holidays/{holiday_id}", response_model=APIResponse[BusinessHolidayRead])
def update_holiday(
    holiday_id: int,
    payload: BusinessHolidayUpdate,
    current_user: User = Depends(require_roles([UserRole.ADMIN.value, UserRole.MANAGER.value])),
    db: Session = Depends(get_db),
):
    service = BusinessHoursService(db)
    holiday = service.update_holiday(holiday_id, payload)
    record_audit(
        db=db,
        action="UPDATE",
        entity_type="BUSINESS_HOURS",
        entity_id=str(holiday.holiday_date),
        details=f"Holiday updated for {holiday.holiday_date}",
        user_email=current_user.email,
        user_id=current_user.id,
    )
    return APIResponse(success=True, message="Holiday updated", data=holiday)


@router.delete("/holidays/{holiday_id}", response_model=APIResponse[dict])
def delete_holiday(
    holiday_id: int,
    current_user: User = Depends(require_roles([UserRole.ADMIN.value, UserRole.MANAGER.value])),
    db: Session = Depends(get_db),
):
    service = BusinessHoursService(db)
    service.delete_holiday(holiday_id)
    record_audit(
        db=db,
        action="DELETE",
        entity_type="BUSINESS_HOURS",
        entity_id=str(holiday_id),
        details=f"Deleted holiday id {holiday_id}",
        user_email=current_user.email,
        user_id=current_user.id,
    )
    return APIResponse(success=True, message="Holiday deleted", data={})
