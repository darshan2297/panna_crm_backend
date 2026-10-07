import enum

from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text

from app.core.database import Base
from app.models.base import TimestampMixin


class IntegrationPlatform(str, enum.Enum):
    ZOMATO = "ZOMATO"
    SWIGGY = "SWIGGY"
    WEBSITE = "WEBSITE"


class IntegrationStatus(str, enum.Enum):
    CONNECTED = "CONNECTED"
    DEGRADED = "DEGRADED"
    DISCONNECTED = "DISCONNECTED"


class IntegrationEnvironment(str, enum.Enum):
    LIVE = "LIVE"
    SANDBOX = "SANDBOX"


class IntegrationConfig(Base, TimestampMixin):
    __tablename__ = "integration_configs"

    platform = Column(String(32), unique=True, nullable=False, index=True)
    is_enabled = Column(Boolean, default=True, nullable=False)
    store_id = Column(String(128), nullable=True)
    api_key_masked = Column(String(128), nullable=True)
    webhook_secret = Column(String(128), nullable=True)
    auto_accept = Column(Boolean, default=True, nullable=False)
    shop_open = Column(Boolean, default=True, nullable=False)  # Live shop open/close toggle
    environment = Column(String(32), default="LIVE", nullable=False)
    status = Column(String(32), default="CONNECTED", nullable=False)
    last_sync_at = Column(DateTime, nullable=True)
    orders_synced_today = Column(Integer, default=0, nullable=False)
    sync_interval_minutes = Column(Integer, default=5, nullable=False)


class IntegrationLog(Base, TimestampMixin):
    __tablename__ = "integration_logs"

    platform = Column(String(32), nullable=False, index=True)
    event_type = Column(
        String(64), nullable=False, index=True
    )  # WEBHOOK_ORDER, WEBHOOK_STATUS, SYNC_ORDERS, SYNC_CATALOG, ERROR
    status = Column(String(32), nullable=False, default="SUCCESS")  # SUCCESS, FAILED, PENDING
    payload_snippet = Column(Text, nullable=True)
    message = Column(Text, nullable=True)
