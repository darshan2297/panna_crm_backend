from sqlalchemy import Column, Integer, String, Text

from app.core.database import Base
from app.models.base import TimestampMixin


class AuditLog(Base, TimestampMixin):
    __tablename__ = "audit_logs"

    user_id = Column(Integer, nullable=True, index=True)
    user_email = Column(String(255), nullable=True, index=True)
    action = Column(String(64), nullable=False, index=True)  # CREATE, UPDATE, DELETE, STATUS_CHANGE, EXPORT, SYNC, LOGIN
    entity_type = Column(String(64), nullable=False, index=True)  # ORDER, INVENTORY, PACKAGING, CUSTOMER, STAFF, MENU, SETTINGS, INTEGRATION
    entity_id = Column(String(128), nullable=True, index=True)
    details = Column(Text, nullable=True)  # JSON or text description of changes
    ip_address = Column(String(64), nullable=True)
