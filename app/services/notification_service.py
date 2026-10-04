import json
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import desc, func
from sqlalchemy.orm import Session

from app.core.exceptions import BadRequestException, NotFoundException
from app.models.inventory import InventoryItem
from app.models.notification import (
    Notification,
    NotificationChannel,
    NotificationChannelStatus,
    NotificationSeverity,
    NotificationType,
)
from app.models.packaging import PackagingItem
from app.schemas.notification import (
    NotificationDispatchResult,
    NotificationSummary,
)
from app.services.notifications.email_adapter import EmailNotificationAdapter
from app.services.notifications.whatsapp_adapter import WhatsAppNotificationAdapter
from app.utils.stock import classify_stock, needs_restock, suggest_reorder_qty


class NotificationService:
    @staticmethod
    def scan_and_generate_stock_alerts(db: Session) -> tuple[int, list[Notification]]:
        """
        Scans all active inventory ingredients and packaging materials for low stock or critical breaches.
        Creates notifications automatically with deduplication (skips if unread alert already active for item).
        """
        new_notifications: list[Notification] = []

        # 1. Scan Ingredients (inventory_items)
        ingredients = db.query(InventoryItem).filter(InventoryItem.is_active == True).all()
        for item in ingredients:
            if needs_restock(item.current_stock, item.reorder_level):
                # Check for existing unread alert
                existing = (
                    db.query(Notification)
                    .filter(
                        Notification.entity_type == "INVENTORY",
                        Notification.entity_id == item.id,
                        Notification.is_read == False,
                    )
                    .first()
                )
                if not existing:
                    status = classify_stock(item.current_stock, item.minimum_stock, item.reorder_level)
                    is_critical = status in ("CRITICAL", "OUT_OF_STOCK")
                    is_zero = status == "OUT_OF_STOCK"
                    severity = (
                        NotificationSeverity.CRITICAL.value if is_critical else NotificationSeverity.WARNING.value
                    )
                    ntype = (
                        NotificationType.OUT_OF_STOCK.value
                        if is_zero
                        else NotificationType.CRITICAL_STOCK.value
                        if is_critical
                        else NotificationType.LOW_STOCK.value
                    )
                    title = f"Kitchen Stock Alert: {item.name}"
                    message = (
                        f"CRITICAL BREACH: {item.name} is depleted ({item.current_stock} {item.unit} remaining). Kitchen minimum is {item.minimum_stock} {item.unit}."
                        if is_critical
                        else f"REORDER WARNING: {item.name} is at {item.current_stock} {item.unit} (reorder threshold is {item.reorder_level} {item.unit})."
                    )

                    metadata = {
                        "item_name": item.name,
                        "sku": item.sku,
                        "unit": item.unit,
                        "current_stock": item.current_stock,
                        "reorder_level": item.reorder_level,
                        "minimum_stock": item.minimum_stock,
                        "suggested_qty": suggest_reorder_qty(item.current_stock, item.reorder_level, min_qty=1.0),
                        "supplier": item.supplier or "Local Mandi / Agro Vendor",
                        "estimated_cost": round(
                            suggest_reorder_qty(item.current_stock, item.reorder_level, min_qty=1.0)
                            * item.purchase_price,
                            2,
                        ),
                    }

                    notif = Notification(
                        title=title,
                        message=message,
                        type=ntype,
                        severity=severity,
                        entity_type="INVENTORY",
                        entity_id=item.id,
                        is_read=False,
                        channel=NotificationChannel.IN_APP.value,
                        channel_status=NotificationChannelStatus.SENT.value,
                        metadata_json=json.dumps(metadata),
                    )
                    db.add(notif)
                    new_notifications.append(notif)

        # 2. Scan Packaging materials (packaging_items)
        packagings = db.query(PackagingItem).filter(PackagingItem.is_active == True).all()
        for item in packagings:
            if needs_restock(item.current_stock, item.reorder_level):
                existing = (
                    db.query(Notification)
                    .filter(
                        Notification.entity_type == "PACKAGING",
                        Notification.entity_id == item.id,
                        Notification.is_read == False,
                    )
                    .first()
                )
                if not existing:
                    status = classify_stock(item.current_stock, item.minimum_stock, item.reorder_level)
                    is_critical = status in ("CRITICAL", "OUT_OF_STOCK")
                    is_zero = status == "OUT_OF_STOCK"
                    severity = (
                        NotificationSeverity.CRITICAL.value if is_critical else NotificationSeverity.WARNING.value
                    )
                    ntype = (
                        NotificationType.OUT_OF_STOCK.value
                        if is_zero
                        else NotificationType.CRITICAL_STOCK.value
                        if is_critical
                        else NotificationType.LOW_STOCK.value
                    )
                    title = f"Packaging Alert: {item.name}"
                    message = (
                        f"CRITICAL SHORTAGE: {item.name} has only {item.current_stock} {item.unit} remaining (safety threshold: {item.minimum_stock} {item.unit})."
                        if is_critical
                        else f"REPLENISHMENT DUE: {item.name} is at {item.current_stock} {item.unit} (reorder threshold is {item.reorder_level} {item.unit})."
                    )

                    metadata = {
                        "item_name": item.name,
                        "sku": item.sku,
                        "unit": item.unit,
                        "current_stock": item.current_stock,
                        "reorder_level": item.reorder_level,
                        "minimum_stock": item.minimum_stock,
                        "suggested_qty": suggest_reorder_qty(
                            item.current_stock, item.reorder_level, min_qty=10.0, whole_units=True
                        ),
                        "supplier": item.supplier or "EcoPackaging India",
                        "estimated_cost": round(
                            suggest_reorder_qty(item.current_stock, item.reorder_level, min_qty=10.0, whole_units=True)
                            * item.purchase_cost,
                            2,
                        ),
                    }

                    notif = Notification(
                        title=title,
                        message=message,
                        type=ntype,
                        severity=severity,
                        entity_type="PACKAGING",
                        entity_id=item.id,
                        is_read=False,
                        channel=NotificationChannel.IN_APP.value,
                        channel_status=NotificationChannelStatus.SENT.value,
                        metadata_json=json.dumps(metadata),
                    )
                    db.add(notif)
                    new_notifications.append(notif)

        if new_notifications:
            db.commit()
            for n in new_notifications:
                db.refresh(n)

        return len(new_notifications), new_notifications

    @staticmethod
    def list_notifications(
        db: Session,
        is_read: bool | None = None,
        ntype: str | None = None,
        severity: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[int, list[Notification]]:
        query = db.query(Notification)
        if is_read is not None:
            query = query.filter(Notification.is_read == is_read)
        if ntype:
            query = query.filter(Notification.type == ntype)
        if severity:
            query = query.filter(Notification.severity == severity)

        total = query.count()
        items = query.order_by(desc(Notification.created_at)).offset(offset).limit(limit).all()
        return total, items

    @staticmethod
    def get_unread_count(db: Session) -> int:
        return db.query(func.count(Notification.id)).filter(Notification.is_read == False).scalar() or 0

    @staticmethod
    def get_summary(db: Session) -> NotificationSummary:
        total = db.query(func.count(Notification.id)).scalar() or 0
        unread = db.query(func.count(Notification.id)).filter(Notification.is_read == False).scalar() or 0
        critical = (
            db.query(func.count(Notification.id))
            .filter(
                Notification.severity == NotificationSeverity.CRITICAL.value,
                Notification.is_read == False,
            )
            .scalar()
            or 0
        )
        warning = (
            db.query(func.count(Notification.id))
            .filter(
                Notification.severity == NotificationSeverity.WARNING.value,
                Notification.is_read == False,
            )
            .scalar()
            or 0
        )
        stock_alerts = (
            db.query(func.count(Notification.id))
            .filter(
                Notification.type.in_(
                    [
                        NotificationType.LOW_STOCK.value,
                        NotificationType.CRITICAL_STOCK.value,
                        NotificationType.OUT_OF_STOCK.value,
                    ]
                ),
                Notification.is_read == False,
            )
            .scalar()
            or 0
        )
        order_alerts = (
            db.query(func.count(Notification.id))
            .filter(
                Notification.type == NotificationType.ORDER_ALERT.value,
                Notification.is_read == False,
            )
            .scalar()
            or 0
        )

        return NotificationSummary(
            total_notifications=total,
            unread_count=unread,
            critical_count=critical,
            warning_count=warning,
            stock_alert_count=stock_alerts,
            order_alert_count=order_alerts,
        )

    @staticmethod
    def mark_as_read(db: Session, notification_id: int) -> Notification | None:
        notif = db.query(Notification).filter(Notification.id == notification_id).first()
        if not notif:
            return None
        notif.mark_read()
        db.commit()
        db.refresh(notif)
        return notif

    @staticmethod
    def mark_all_as_read(db: Session) -> int:
        count = (
            db.query(Notification)
            .filter(Notification.is_read == False)
            .update(
                {
                    "is_read": True,
                    "read_at": datetime.now(UTC),
                },
                synchronize_session=False,
            )
        )
        db.commit()
        return count

    @staticmethod
    def delete_notification(db: Session, notification_id: int) -> bool:
        notif = db.query(Notification).filter(Notification.id == notification_id).first()
        if not notif:
            return False
        db.delete(notif)
        db.commit()
        return True

    @staticmethod
    def dispatch_notification(
        db: Session,
        notification_id: int,
        channel: str,
        recipient: str | None = None,
        custom_message: str | None = None,
    ) -> NotificationDispatchResult:
        notif = db.query(Notification).filter(Notification.id == notification_id).first()
        if not notif:
            raise NotFoundException("Notification", notification_id)

        meta: dict[str, Any] = {}
        if notif.metadata_json:
            try:
                meta = json.loads(notif.metadata_json)
            except Exception:
                meta = {}

        dispatch_text = custom_message or notif.message

        if channel.upper() == "WHATSAPP":
            adapter = WhatsAppNotificationAdapter()
            result = adapter.dispatch(
                title=notif.title,
                message=dispatch_text,
                severity=notif.severity,
                recipient=recipient,
                metadata=meta,
            )
        elif channel.upper() == "EMAIL":
            adapter = EmailNotificationAdapter()
            result = adapter.dispatch(
                title=notif.title,
                message=dispatch_text,
                severity=notif.severity,
                recipient=recipient,
                metadata=meta,
            )
        else:
            raise BadRequestException(f"Unsupported dispatch channel: {channel}")

        notif.channel = channel.upper()
        notif.channel_status = result["status"]
        if recipient:
            notif.recipient = recipient
        db.commit()

        return NotificationDispatchResult(
            notification_id=notif.id,
            channel=result["channel"],
            recipient=result["recipient"],
            status=result["status"],
            preview_content=result["preview_content"],
            action_url=result.get("action_url"),
            dispatched_at=result["dispatched_at"],
        )
