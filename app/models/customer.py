from enum import Enum as PyEnum

from sqlalchemy import Column, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.models.base import TimestampMixin


class CustomerSegment(str, PyEnum):
    NEW = "NEW"
    REGULAR = "REGULAR"
    VIP = "VIP"
    LAPSED = "LAPSED"


class Customer(Base, TimestampMixin):
    __tablename__ = "customers"

    name = Column(String(255), nullable=False)
    phone = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(255), nullable=True)
    default_address = Column(Text, nullable=True)

    total_orders = Column(Integer, default=0, nullable=False)
    total_spent = Column(Float, default=0.0, nullable=False)

    # CRM enrichment fields (Phase 10)
    notes = Column(Text, nullable=True)
    segment = Column(String(20), default=CustomerSegment.NEW.value, index=True, nullable=False)
    last_order_date = Column(DateTime, index=True, nullable=True)

    # Relationships
    orders = relationship("Order", back_populates="customer")

    @property
    def average_order_value(self) -> float:
        if self.total_orders > 0:
            return round(self.total_spent / self.total_orders, 2)
        return 0.0

    def __repr__(self) -> str:
        return f"<Customer {self.name} ({self.phone}) [{self.segment}]>"
