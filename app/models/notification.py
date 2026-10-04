import enum
from datetime import UTC, datetime

from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text

from app.core.database import Base
from app.models.base import TimestampMixin


class NotificationType(str, enum.Enum):
    LOW_STOCK = "LOW_STOCK"
    CRITICAL_STOCK = "CRITICAL_STOCK"
    OUT_OF_STOCK = "OUT_OF_STOCK"
    RESTOCK_PO = "RESTOCK_PO"
    ORDER_ALERT = "ORDER_ALERT"
    SYSTEM = "SYSTEM"


class NotificationSeverity(str, enum.Enum):
    INFO = "INFO"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"
    SUCCESS = "SUCCESS"


class NotificationChannel(str, enum.Enum):
    IN_APP = "IN_APP"
    EMAIL = "EMAIL"
    WHATSAPP = "WHATSAPP"


class NotificationChannelStatus(str, enum.Enum):
    PENDING = "PENDING"
    SENT = "SENT"
    MOCK_DELIVERED = "MOCK_DELIVERED"
    FAILED = "FAILED"


class Notification(Base, TimestampMixin):
    __tablename__ = "notifications"

    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    type = Column(String(50), default=NotificationType.LOW_STOCK.value, nullable=False, index=True)
    severity = Column(String(50), default=NotificationSeverity.WARNING.value, nullable=False, index=True)
    entity_type = Column(String(50), nullable=True)  # INVENTORY, PACKAGING, ORDER, RESTOCK_PO
    entity_id = Column(Integer, nullable=True)
    is_read = Column(Boolean, default=False, nullable=False, index=True)
    channel = Column(String(50), default=NotificationChannel.IN_APP.value, nullable=False)
    channel_status = Column(String(50), default=NotificationChannelStatus.SENT.value, nullable=False)
    recipient = Column(String(255), nullable=True)  # Email or WhatsApp phone
    metadata_json = Column(Text, nullable=True)  # JSON formatted extra context
    read_at = Column(DateTime, nullable=True)

    def mark_read(self) -> None:
        self.is_read = True
        self.read_at = datetime.now(UTC)

    def __repr__(self) -> str:
        return f"<Notification {self.id}: {self.type} - {self.title}>"
