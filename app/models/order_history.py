from sqlalchemy import Column, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.models.base import TimestampMixin


class OrderStatusHistory(Base, TimestampMixin):
    __tablename__ = "order_status_history"

    order_id = Column(Integer, ForeignKey("orders.id", ondelete="CASCADE"), nullable=False, index=True)
    previous_status = Column(String(50), nullable=True)
    new_status = Column(String(50), nullable=False)
    changed_by_name = Column(String(255), default="System", nullable=False)
    notes = Column(Text, nullable=True)

    order = relationship("Order", back_populates="status_history")

    def __repr__(self) -> str:
        return f"<OrderStatusHistory #{self.order_id}: {self.previous_status} -> {self.new_status}>"
