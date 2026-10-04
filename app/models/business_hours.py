from sqlalchemy import Boolean, Column, Date, Integer, String

from app.core.database import Base
from app.models.base import TimestampMixin


class BusinessHoursConfig(Base, TimestampMixin):
    """Singleton-style global configuration for storefront operating hours."""

    __tablename__ = "business_hours_config"

    # When disabled, the shop ignores the weekly schedule and holiday calendar
    # (only the per-platform manual shop_open master switch applies).
    auto_schedule_enabled = Column(Boolean, default=True, nullable=False)
    # Temporary override: keep the shop open even outside the schedule/holidays.
    force_open_now = Column(Boolean, default=False, nullable=False)
    timezone = Column(String(64), default="Asia/Kolkata", nullable=False)
    holiday_message = Column(String(255), default="We are closed today. See you tomorrow!", nullable=True)


class BusinessHourDay(Base, TimestampMixin):
    """Weekly recurring opening hours, one row per weekday."""

    __tablename__ = "business_hour_days"

    day_of_week = Column(Integer, unique=True, nullable=False, index=True)  # 0=Monday .. 6=Sunday
    is_open = Column(Boolean, default=True, nullable=False)
    open_time = Column(String(5), default="17:00", nullable=False)  # HH:MM (24h) local time
    close_time = Column(String(5), default="23:00", nullable=False)  # HH:MM (24h) local time


class BusinessHoliday(Base, TimestampMixin):
    """Date-specific override: full closure or custom hours for a single day."""

    __tablename__ = "business_holidays"

    holiday_date = Column(Date, unique=True, nullable=False, index=True)
    is_closed = Column(Boolean, default=True, nullable=False)
    open_time = Column(String(5), nullable=True)  # used only when is_closed is False
    close_time = Column(String(5), nullable=True)
    reason = Column(String(255), nullable=True)
