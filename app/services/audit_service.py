from datetime import UTC, datetime, timedelta

from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog
from app.schemas.audit import AuditLogRead, AuditStats


class AuditService:
    def __init__(self, db: Session):
        self.db = db
        self._ensure_seed_logs()

    def _ensure_seed_logs(self):
        count = self.db.query(AuditLog).count()
        if count == 0:
            now = datetime.now(UTC)
            sample_logs = [
                {
                    "user_email": "admin@pannabiryani.com",
                    "action": "LOGIN",
                    "entity_type": "STAFF",
                    "entity_id": "1",
                    "details": "Administrator signed in from web console",
                    "ip_address": "127.0.0.1",
                    "time_offset_min": 180,
                },
                {
                    "user_email": "admin@pannabiryani.com",
                    "action": "UPDATE",
                    "entity_type": "MENU",
                    "entity_id": "1",
                    "details": "Updated portion price for Chicken Dum Biryani (1kg)",
                    "ip_address": "127.0.0.1",
                    "time_offset_min": 140,
                },
                {
                    "user_email": "manager@pannabiryani.com",
                    "action": "STATUS_CHANGE",
                    "entity_type": "ORDER",
                    "entity_id": "WEB-10492",
                    "details": "Status advanced from PREPARING to READY",
                    "ip_address": "192.168.1.12",
                    "time_offset_min": 110,
                },
                {
                    "user_email": "manager@pannabiryani.com",
                    "action": "CREATE",
                    "entity_type": "PURCHASE_ORDER",
                    "entity_id": "PO-2026-004",
                    "details": "Generated purchase order for Basmati Rice (100kg)",
                    "ip_address": "192.168.1.12",
                    "time_offset_min": 75,
                },
                {
                    "user_email": "system@pannabiryani.com",
                    "action": "SYNC",
                    "entity_type": "INTEGRATION",
                    "entity_id": "ZOMATO",
                    "details": "Automated order sync pulled 4 pending partner tickets",
                    "ip_address": "10.0.0.1",
                    "time_offset_min": 45,
                },
                {
                    "user_email": "admin@pannabiryani.com",
                    "action": "EXPORT",
                    "entity_type": "ANALYTICS",
                    "entity_id": "SALES_CSV",
                    "details": "Exported 30-day Sales Trend report to CSV",
                    "ip_address": "127.0.0.1",
                    "time_offset_min": 15,
                },
            ]

            for s in sample_logs:
                log = AuditLog(
                    user_email=s["user_email"],
                    action=s["action"],
                    entity_type=s["entity_type"],
                    entity_id=s["entity_id"],
                    details=s["details"],
                    ip_address=s["ip_address"],
                    created_at=now - timedelta(minutes=s["time_offset_min"]),
                )
                self.db.add(log)
            self.db.commit()

    def record(
        self,
        action: str,
        entity_type: str,
        entity_id: str | None = None,
        details: str | None = None,
        user_email: str | None = None,
        user_id: int | None = None,
        ip_address: str | None = None,
    ) -> AuditLog:
        log = AuditLog(
            action=action.upper(),
            entity_type=entity_type.upper(),
            entity_id=str(entity_id) if entity_id else None,
            details=details,
            user_email=user_email,
            user_id=user_id,
            ip_address=ip_address or "127.0.0.1",
            created_at=datetime.now(UTC),
        )
        self.db.add(log)
        self.db.commit()
        self.db.refresh(log)
        return log

    def get_logs(
        self,
        page: int = 1,
        page_size: int = 20,
        action: str | None = None,
        entity_type: str | None = None,
        search: str | None = None,
        user_email: str | None = None,
    ) -> tuple[list[AuditLogRead], int]:
        q = self.db.query(AuditLog)

        if action and action != "ALL":
            q = q.filter(AuditLog.action == action.upper())

        if entity_type and entity_type != "ALL":
            q = q.filter(AuditLog.entity_type == entity_type.upper())

        if user_email:
            q = q.filter(AuditLog.user_email.ilike(f"%{user_email}%"))

        if search:
            s = f"%{search}%"
            q = q.filter(
                or_(
                    AuditLog.details.ilike(s),
                    AuditLog.entity_id.ilike(s),
                    AuditLog.user_email.ilike(s),
                )
            )

        total = q.count()
        logs = q.order_by(AuditLog.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()
        return [AuditLogRead.from_orm(l) for l in logs], total

    def get_stats(self) -> AuditStats:
        total = self.db.query(AuditLog).count()
        now = datetime.now(UTC)
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0, tzinfo=None)
        today_count = self.db.query(AuditLog).filter(AuditLog.created_at >= today_start).count()

        by_action_rows = (
            self.db.query(AuditLog.action, func.count(AuditLog.id))
            .group_by(AuditLog.action)
            .all()
        )
        by_action = {r[0]: r[1] for r in by_action_rows}

        by_entity_rows = (
            self.db.query(AuditLog.entity_type, func.count(AuditLog.id))
            .group_by(AuditLog.entity_type)
            .all()
        )
        by_entity = {r[0]: r[1] for r in by_entity_rows}

        return AuditStats(
            total_logs=total,
            today_logs=today_count,
            by_action=by_action,
            by_entity=by_entity,
        )


def record_audit(
    db: Session,
    action: str,
    entity_type: str,
    entity_id: str | None = None,
    details: str | None = None,
    user_email: str | None = None,
    user_id: int | None = None,
    ip_address: str | None = None,
):
    try:
        service = AuditService(db)
        return service.record(
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            details=details,
            user_email=user_email,
            user_id=user_id,
            ip_address=ip_address,
        )
    except Exception as e:
        # Prevent audit logging failure from failing main request
        print(f"Error recording audit log: {e}")
        return None
