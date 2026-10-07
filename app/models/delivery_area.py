"""DeliveryArea model for storefront delivery zones with per-area fees and ETAs."""

from sqlalchemy import Boolean, Column, Float, Integer, String

from app.core.database import Base
from app.models.base import TimestampMixin


class DeliveryArea(Base, TimestampMixin):
    __tablename__ = "delivery_areas"

    name = Column(String(255), nullable=False)
    pincode = Column(String(20), nullable=False, index=True)
    delivery_fee = Column(Float, default=0.0, nullable=False)
    estimated_minutes = Column(Integer, default=45, nullable=False)
    min_order = Column(Float, default=0.0, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    sort_order = Column(Integer, default=0, nullable=False)

    def __repr__(self) -> str:
        return f"<DeliveryArea {self.name} ({self.pincode})>"
