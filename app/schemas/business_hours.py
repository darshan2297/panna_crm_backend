from datetime import date, datetime

from pydantic import BaseModel, Field


class BusinessHourDayRead(BaseModel):
    id: int
    day_of_week: int = Field(..., description="0=Monday .. 6=Sunday")
    day_name: str
    is_open: bool
    open_time: str
    close_time: str

    class Config:
        from_attributes = True


class BusinessHourDayUpdate(BaseModel):
    is_open: bool | None = None
    open_time: str | None = Field(None, pattern=r"^([01]\d|2[0-3]):[0-5]\d$")
    close_time: str | None = Field(None, pattern=r"^([01]\d|2[0-3]):[0-5]\d$")


class BusinessHolidayBase(BaseModel):
    holiday_date: date
    is_closed: bool = True
    open_time: str | None = Field(None, pattern=r"^([01]\d|2[0-3]):[0-5]\d$")
    close_time: str | None = Field(None, pattern=r"^([01]\d|2[0-3]):[0-5]\d$")
    reason: str | None = None


class BusinessHolidayCreate(BusinessHolidayBase):
    pass


class BusinessHolidayUpdate(BaseModel):
    is_closed: bool | None = None
    open_time: str | None = None
    close_time: str | None = None
    reason: str | None = None


class BusinessHolidayRead(BusinessHolidayBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


class BusinessHoursConfigRead(BaseModel):
    auto_schedule_enabled: bool
    force_open_now: bool
    timezone: str
    holiday_message: str | None = None
    updated_at: datetime

    class Config:
        from_attributes = True


class BusinessHoursConfigUpdate(BaseModel):
    auto_schedule_enabled: bool | None = None
    force_open_now: bool | None = None
    timezone: str | None = None
    holiday_message: str | None = None


class BusinessHoursRead(BaseModel):
    """Full business-hours payload for the CRM management screen."""

    config: BusinessHoursConfigRead
    days: list[BusinessHourDayRead]
    holidays: list[BusinessHolidayRead]


class PublicBusinessHours(BaseModel):
    """Facing the storefront: current open state plus display strings."""

    is_open: bool
    auto_schedule_enabled: bool
    display_hours: str
    status_text: str
    next_open_text: str | None = None
    holiday_message: str | None = None
    full_schedule: dict[str, str] = Field(default_factory=dict)


class ShopStatusResponse(BaseModel):
    """Public shop status resolving manual master switch + schedule across channels."""

    platforms: dict[str, bool]
    website_open: bool
    zomato_open: bool
    swiggy_open: bool
    is_open: bool
    status_text: str = "Open Now"
    next_open_text: str | None = None
    display_hours: str | None = None
    holiday_message: str | None = None
    manual_override: dict[str, bool] = Field(default_factory=dict)
    schedule_active: bool
    business_hours: PublicBusinessHours
