from datetime import UTC, date, datetime, time, timedelta

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.models.business_hours import (
    BusinessHoliday,
    BusinessHourDay,
    BusinessHoursConfig,
)
from app.schemas.business_hours import (
    BusinessHolidayCreate,
    BusinessHolidayRead,
    BusinessHolidayUpdate,
    BusinessHourDayRead,
    BusinessHourDayUpdate,
    BusinessHoursConfigRead,
    BusinessHoursConfigUpdate,
    PublicBusinessHours,
)
from app.socket_manager import emit_event

DAY_NAMES = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


def _parse_time(value: str) -> time:
    hours, minutes = value.split(":")
    return time(int(hours), int(minutes))


def _format_time_12h(value: str) -> str:
    t = _parse_time(value)
    suffix = "AM" if t.hour < 12 else "PM"
    hour12 = t.hour % 12 or 12
    return f"{hour12}:{t.minute:02d} {suffix}"


def _local_now(tz_name: str) -> datetime:
    """Return current wall-clock time for the kitchen timezone."""
    try:
        from zoneinfo import ZoneInfo

        return datetime.now(ZoneInfo(tz_name))
    except Exception:
        # Fallback: fixed IST offset (UTC+5:30) when tz database is unavailable (e.g. bare Windows).
        return datetime.now(UTC) + timedelta(hours=5, minutes=30)


class BusinessHoursService:
    def __init__(self, db: Session):
        self.db = db
        self._ensure_tables()
        self._ensure_seed()

    # ────────────────────────── Schema safety ──────────────────────────
    def _ensure_tables(self):
        """
        Guarantee the business-hours tables exist even if the app's startup
        ``create_all`` did not run (e.g. a long-running process started before
        this feature was deployed, scripts, or a stale database).
        """
        try:
            self.db.query(BusinessHoursConfig).first()
            return
        except SQLAlchemyError:
            self.db.rollback()

        try:
            bind = self.db.get_bind()
            BusinessHoursConfig.__table__.create(bind=bind, checkfirst=True)
            BusinessHourDay.__table__.create(bind=bind, checkfirst=True)
            BusinessHoliday.__table__.create(bind=bind, checkfirst=True)
        except SQLAlchemyError:
            self.db.rollback()

    # ────────────────────────── Seeding ──────────────────────────
    def _ensure_seed(self):
        config = self.db.query(BusinessHoursConfig).first()
        if not config:
            self.db.add(BusinessHoursConfig(auto_schedule_enabled=True, timezone="Asia/Kolkata"))
            self.db.flush()

        existing_days = {d.day_of_week for d in self.db.query(BusinessHourDay).all()}
        for dow in range(7):
            if dow not in existing_days:
                # Default: Mon-Fri 5 PM - 11 PM, Sat-Sun 11 AM - 11 PM
                is_weekend = dow >= 5
                self.db.add(
                    BusinessHourDay(
                        day_of_week=dow,
                        is_open=True,
                        open_time="11:00" if is_weekend else "17:00",
                        close_time="23:00",
                    )
                )
        self.db.commit()

    # ────────────────────────── Reads ──────────────────────────
    def get_config(self) -> BusinessHoursConfig:
        return self.db.query(BusinessHoursConfig).first()

    def get_days(self) -> list[BusinessHourDay]:
        return self.db.query(BusinessHourDay).order_by(BusinessHourDay.day_of_week).all()

    def get_holidays(self) -> list[BusinessHoliday]:
        return self.db.query(BusinessHoliday).order_by(BusinessHoliday.holiday_date).all()

    def get_full(self) -> dict:
        return {
            "config": BusinessHoursConfigRead.model_validate(self.get_config()),
            "days": [self._day_to_read(d) for d in self.get_days()],
            "holidays": [BusinessHolidayRead.model_validate(h) for h in self.get_holidays()],
        }

    def _day_to_read(self, day: BusinessHourDay) -> BusinessHourDayRead:
        dow = day.day_of_week if isinstance(day.day_of_week, int) and 0 <= day.day_of_week <= 6 else 0
        return BusinessHourDayRead(
            id=day.id,
            day_of_week=dow,
            day_name=DAY_NAMES[dow],
            is_open=day.is_open,
            open_time=day.open_time,
            close_time=day.close_time,
        )

    # ────────────────────────── Writes ──────────────────────────
    def update_config(self, payload: BusinessHoursConfigUpdate) -> BusinessHoursConfigRead:
        config = self.get_config()
        if payload.auto_schedule_enabled is not None:
            config.auto_schedule_enabled = payload.auto_schedule_enabled
        if payload.force_open_now is not None:
            config.force_open_now = payload.force_open_now
        if payload.timezone is not None:
            config.timezone = payload.timezone
        if payload.holiday_message is not None:
            config.holiday_message = payload.holiday_message
        self.db.commit()
        self.db.refresh(config)
        self._emit_status_change()
        return BusinessHoursConfigRead.model_validate(config)

    def update_day(self, day_of_week: int, payload: BusinessHourDayUpdate) -> BusinessHourDayRead:
        if day_of_week < 0 or day_of_week > 6:
            raise ValueError("day_of_week must be between 0 (Monday) and 6 (Sunday)")
        day = self.db.query(BusinessHourDay).filter(BusinessHourDay.day_of_week == day_of_week).first()
        if not day:
            day = BusinessHourDay(day_of_week=day_of_week)
            self.db.add(day)

        if payload.is_open is not None:
            day.is_open = payload.is_open
        if payload.open_time is not None:
            day.open_time = payload.open_time
        if payload.close_time is not None:
            day.close_time = payload.close_time

        self.db.commit()
        self.db.refresh(day)
        self._emit_status_change()
        return self._day_to_read(day)

    def create_or_update_holiday(self, payload: BusinessHolidayCreate) -> BusinessHolidayRead:
        holiday = (
            self.db.query(BusinessHoliday)
            .filter(BusinessHoliday.holiday_date == payload.holiday_date)
            .first()
        )
        if not holiday:
            holiday = BusinessHoliday(holiday_date=payload.holiday_date)
            self.db.add(holiday)

        holiday.is_closed = payload.is_closed
        holiday.open_time = None if payload.is_closed else payload.open_time
        holiday.close_time = None if payload.is_closed else payload.close_time
        holiday.reason = payload.reason

        self.db.commit()
        self.db.refresh(holiday)
        self._emit_status_change()
        return BusinessHolidayRead.model_validate(holiday)

    def update_holiday(self, holiday_id: int, payload: BusinessHolidayUpdate) -> BusinessHolidayRead:
        holiday = self.db.query(BusinessHoliday).filter(BusinessHoliday.id == holiday_id).first()
        if not holiday:
            raise ValueError("Holiday not found")

        if payload.is_closed is not None:
            holiday.is_closed = payload.is_closed
        if payload.open_time is not None:
            holiday.open_time = payload.open_time
        if payload.close_time is not None:
            holiday.close_time = payload.close_time
        if payload.reason is not None:
            holiday.reason = payload.reason
        if holiday.is_closed:
            holiday.open_time = None
            holiday.close_time = None

        self.db.commit()
        self.db.refresh(holiday)
        self._emit_status_change()
        return BusinessHolidayRead.model_validate(holiday)

    def delete_holiday(self, holiday_id: int) -> None:
        holiday = self.db.query(BusinessHoliday).filter(BusinessHoliday.id == holiday_id).first()
        if not holiday:
            raise ValueError("Holiday not found")
        self.db.delete(holiday)
        self.db.commit()
        self._emit_status_change()

    # ────────────────────────── Schedule resolution ──────────────────────────
    def resolve_public(self, now_local: datetime | None = None) -> PublicBusinessHours:
        config = self.get_config()
        tz_name = config.timezone or "Asia/Kolkata"
        now = now_local or _local_now(tz_name)

        # Temporary manual override: keep the shop open even outside schedule/holidays.
        if config.force_open_now:
            return PublicBusinessHours(
                is_open=True,
                auto_schedule_enabled=bool(config.auto_schedule_enabled),
                display_hours="Open now (extended hours)",
                status_text="Open Now",
                next_open_text=None,
                holiday_message=None,
                full_schedule=self._full_schedule_map(),
            )

        # When the auto schedule is disabled, hours never gate the shop.
        if not config.auto_schedule_enabled:
            return PublicBusinessHours(
                is_open=True,
                auto_schedule_enabled=False,
                display_hours="Open as per manual control",
                status_text="Accepting Orders",
                next_open_text=None,
                holiday_message=None,
                full_schedule=self._full_schedule_map(),
            )

        today = now.date()
        minutes_now = now.hour * 60 + now.minute

        holiday = (
            self.db.query(BusinessHoliday)
            .filter(BusinessHoliday.holiday_date == today)
            .first()
        )

        if holiday is not None:
            if holiday.is_closed:
                return PublicBusinessHours(
                    is_open=False,
                    auto_schedule_enabled=True,
                    display_hours="Closed Today",
                    status_text=config.holiday_message or "We are closed today. See you tomorrow!",
                    next_open_text=self._next_open_text(now),
                    holiday_message=config.holiday_message,
                    full_schedule=self._full_schedule_map(),
                )
            open_time = holiday.open_time or "17:00"
            close_time = holiday.close_time or "23:00"
            is_open, status = self._window_state(minutes_now, open_time, close_time)
            return PublicBusinessHours(
                is_open=is_open,
                auto_schedule_enabled=True,
                display_hours=f"{_format_time_12h(open_time)} - {_format_time_12h(close_time)}",
                status_text=status,
                next_open_text=None if is_open else self._next_open_text(now),
                holiday_message=None,
                full_schedule=self._full_schedule_map(),
            )

        day = (
            self.db.query(BusinessHourDay)
            .filter(BusinessHourDay.day_of_week == now.weekday())
            .first()
        )

        if day is None or not day.is_open:
            return PublicBusinessHours(
                is_open=False,
                auto_schedule_enabled=True,
                display_hours="Closed Today",
                status_text="We are closed today.",
                next_open_text=self._next_open_text(now),
                holiday_message=None,
                full_schedule=self._full_schedule_map(),
            )

        is_open, status = self._window_state(minutes_now, day.open_time, day.close_time)
        return PublicBusinessHours(
            is_open=is_open,
            auto_schedule_enabled=True,
            display_hours=f"{_format_time_12h(day.open_time)} - {_format_time_12h(day.close_time)}",
            status_text=status,
            next_open_text=None if is_open else self._next_open_text(now),
            holiday_message=None,
            full_schedule=self._full_schedule_map(),
        )

    def _window_state(self, minutes_now: int, open_time: str, close_time: str) -> tuple[bool, str]:
        open_min = _parse_time(open_time).hour * 60 + _parse_time(open_time).minute
        close_min = _parse_time(close_time).hour * 60 + _parse_time(close_time).minute

        if close_min <= open_min:
            # Overnight window (e.g. 20:00 -> 02:00)
            is_open = minutes_now >= open_min or minutes_now < close_min
        else:
            is_open = open_min <= minutes_now < close_min

        if is_open:
            return True, "Open Now"
        if minutes_now < open_min:
            return False, f"Opens at {_format_time_12h(open_time)}"
        return False, "Closed for today"

    def _full_schedule_map(self) -> dict[str, str]:
        schedule: dict[str, str] = {}
        for day in self.get_days():
            if not isinstance(day.day_of_week, int) or not 0 <= day.day_of_week <= 6:
                continue
            if day.is_open:
                schedule[DAY_NAMES[day.day_of_week]] = (
                    f"{_format_time_12h(day.open_time)} - {_format_time_12h(day.close_time)}"
                )
            else:
                schedule[DAY_NAMES[day.day_of_week]] = "Closed"
        return schedule

    def _next_open_text(self, now: datetime) -> str | None:
        """Find the next opening window within the next 7 days."""
        for offset in range(0, 8):
            candidate = now + timedelta(days=offset)
            candidate_date: date = candidate.date()

            holiday = (
                self.db.query(BusinessHoliday)
                .filter(BusinessHoliday.holiday_date == candidate_date)
                .first()
            )
            if holiday is not None:
                if holiday.is_closed:
                    continue
                open_time, close_time = holiday.open_time, holiday.close_time
            else:
                day = (
                    self.db.query(BusinessHourDay)
                    .filter(BusinessHourDay.day_of_week == candidate.weekday())
                    .first()
                )
                if day is None or not day.is_open:
                    continue
                open_time, close_time = day.open_time, day.close_time

            if not open_time or not close_time:
                continue

            open_dt = datetime.combine(candidate_date, _parse_time(open_time), tzinfo=now.tzinfo)
            close_dt = datetime.combine(candidate_date, _parse_time(close_time), tzinfo=now.tzinfo)
            # Skip today's window if it has already passed.
            if candidate_date == now.date() and now >= close_dt:
                continue

            if candidate_date == now.date() and now < open_dt:
                return f"Today at {_format_time_12h(open_time)}"
            if offset == 0:
                return f"Today at {_format_time_12h(open_time)}"
            if offset == 1:
                return f"Tomorrow at {_format_time_12h(open_time)}"
            return f"{DAY_NAMES[candidate.weekday()]} at {_format_time_12h(open_time)}"
        return None

    def _emit_status_change(self):
        try:
            public = self.resolve_public()
            emit_event("shop_status_changed", {"platform": "ALL", "shop_open": public.is_open})
        except Exception:
            pass


def resolve_shop_status(db: Session) -> dict:
    """
    Combine the per-platform manual master switch with the global schedule.

    Rules (per user decision - manual toggle is the master switch):
      * Manual closed  -> channel is always closed, regardless of schedule.
      * Manual open + auto schedule disabled -> open.
      * Manual open + force_open_now -> open.
      * Manual open + auto schedule enabled -> only open inside schedule/holidays.
    """
    from app.models.integration import IntegrationConfig

    service = BusinessHoursService(db)
    public = service.resolve_public()
    config = service.get_config()

    force_open = bool(config.force_open_now)
    schedule_open = (
        True
        if not config.auto_schedule_enabled
        else bool(public.is_open or force_open)
    )

    # Known sales channels default to open if no config row exists yet.
    known_platforms = ["ZOMATO", "SWIGGY", "WEBSITE", "ONDC"]
    manual: dict[str, bool] = {p: True for p in known_platforms}
    for cfg in db.query(IntegrationConfig).all():
        manual[cfg.platform] = bool(cfg.shop_open)

    platforms: dict[str, bool] = {}
    for platform, is_manual_open in manual.items():
        if not is_manual_open:
            platforms[platform] = False
        else:
            platforms[platform] = bool(schedule_open)

    website_open = platforms.get("WEBSITE", True)
    manual_closed = not manual.get("WEBSITE", True)

    # Derive customer-facing text from the *resolved* website state, so a manual
    # close is never reported as "Open Now" even if the schedule says open.
    if manual_closed:
        status_text = "We are currently closed."
        next_open_text = None
    else:
        status_text = public.status_text
        next_open_text = public.next_open_text

    return {
        "platforms": platforms,
        "website_open": website_open,
        "zomato_open": platforms.get("ZOMATO", True),
        "swiggy_open": platforms.get("SWIGGY", True),
        "is_open": website_open,
        "status_text": status_text,
        "next_open_text": next_open_text,
        "display_hours": public.display_hours,
        "holiday_message": config.holiday_message,
        "manual_override": manual,
        "schedule_active": bool(config.auto_schedule_enabled),
        "business_hours": public,
    }
