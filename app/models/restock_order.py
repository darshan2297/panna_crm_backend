import enum

from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.models.base import TimestampMixin


class RestockOrderStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    ORDERED = "ORDERED"
    RECEIVED = "RECEIVED"
    CANCELLED = "CANCELLED"


class RestockOrderTarget(str, enum.Enum):
    INVENTORY = "INVENTORY"
    PACKAGING = "PACKAGING"
    MIXED = "MIXED"


class RestockOrder(Base, TimestampMixin):
    __tablename__ = "restock_orders"

    po_number = Column(String(100), unique=True, index=True, nullable=False)
    supplier_name = Column(String(255), nullable=False)
    supplier_contact = Column(String(255), nullable=True)
    status = Column(String(50), default=RestockOrderStatus.DRAFT.value, nullable=False, index=True)
    target_type = Column(String(50), default=RestockOrderTarget.INVENTORY.value, nullable=False)
    total_estimated_cost = Column(Float, default=0.0, nullable=False)
    notes = Column(Text, nullable=True)
    created_by_name = Column(String(255), default="Kitchen Manager", nullable=False)
    ordered_at = Column(DateTime, nullable=True)
    received_at = Column(DateTime, nullable=True)

    items = relationship(
        "RestockOrderItem",
        back_populates="restock_order",
        cascade="all, delete-orphan",
        order_by="RestockOrderItem.id",
    )

    def __repr__(self) -> str:
        return f"<RestockOrder {self.po_number}: {self.supplier_name} ({self.status})>"


class RestockOrderItem(Base):
    __tablename__ = "restock_order_items"

    id = Column(Integer, primary_key=True, index=True)
    restock_order_id = Column(Integer, ForeignKey("restock_orders.id", ondelete="CASCADE"), nullable=False)
    item_type = Column(String(50), default="INVENTORY", nullable=False)  # INVENTORY or PACKAGING
    item_id = Column(Integer, nullable=False)
    item_name = Column(String(255), nullable=False)
    item_sku = Column(String(100), nullable=False)
    unit = Column(String(50), default="kg", nullable=False)
    current_stock = Column(Float, default=0.0, nullable=False)
    reorder_threshold = Column(Float, default=0.0, nullable=False)
    suggested_quantity = Column(Float, default=0.0, nullable=False)
    ordered_quantity = Column(Float, default=0.0, nullable=False)
    unit_cost = Column(Float, default=0.0, nullable=False)
    total_cost = Column(Float, default=0.0, nullable=False)
    is_received = Column(Boolean, default=False, nullable=False)

    restock_order = relationship("RestockOrder", back_populates="items")

    def __repr__(self) -> str:
        return f"<RestockOrderItem {self.item_name}: {self.ordered_quantity}{self.unit}>"
