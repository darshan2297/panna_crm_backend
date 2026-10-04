import enum
from datetime import UTC, datetime

from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.models.base import TimestampMixin


class InventoryCategory(str, enum.Enum):
    GRAIN = "GRAIN"
    MEAT = "MEAT"
    DAIRY = "DAIRY"
    VEGETABLE = "VEGETABLE"
    SPICE = "SPICE"
    OIL = "OIL"
    PACKAGING = "PACKAGING"
    OTHER = "OTHER"


class InventoryTransactionType(str, enum.Enum):
    STOCK_IN = "STOCK_IN"
    STOCK_OUT = "STOCK_OUT"
    WASTAGE = "WASTAGE"
    AUDIT_CORRECTION = "AUDIT_CORRECTION"


class InventoryItem(Base, TimestampMixin):
    __tablename__ = "inventory_items"

    name = Column(String(255), unique=True, index=True, nullable=False)
    sku = Column(String(100), unique=True, index=True, nullable=False)
    category = Column(String(50), default="GRAIN", nullable=False)
    unit = Column(String(50), default="kg", nullable=False)  # kg, g, l, ml, piece, packet, pcs
    current_stock = Column(Float, default=0.0, nullable=False)
    minimum_stock = Column(Float, default=10.0, nullable=False)
    reorder_level = Column(Float, default=15.0, nullable=False)
    purchase_price = Column(Float, default=0.0, nullable=False)
    supplier = Column(String(255), nullable=True)
    storage_location = Column(String(255), nullable=True)
    description = Column(String(500), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)

    transactions = relationship(
        "InventoryTransaction",
        back_populates="item",
        cascade="all, delete-orphan",
        order_by="desc(InventoryTransaction.created_at)",
    )

    @property
    def is_low_stock(self) -> bool:
        return self.current_stock <= self.reorder_level

    @property
    def is_critical_stock(self) -> bool:
        return self.current_stock <= self.minimum_stock

    @property
    def total_valuation(self) -> float:
        return round(self.current_stock * self.purchase_price, 2)

    def __repr__(self) -> str:
        return f"<InventoryItem {self.name}: {self.current_stock}{self.unit}>"


class InventoryTransaction(Base):
    __tablename__ = "inventory_transactions"

    id = Column(Integer, primary_key=True, index=True)
    inventory_item_id = Column(
        Integer, ForeignKey("inventory_items.id", ondelete="CASCADE"), nullable=False, index=True
    )
    transaction_type = Column(String(50), nullable=False, index=True)  # STOCK_IN, STOCK_OUT, WASTAGE, AUDIT_CORRECTION
    quantity = Column(Float, nullable=False)
    stock_before = Column(Float, nullable=False)
    stock_after = Column(Float, nullable=False)
    unit_price = Column(Float, nullable=True)
    total_cost = Column(Float, nullable=True)
    reference_no = Column(String(100), nullable=True)
    notes = Column(Text, nullable=True)
    performed_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)

    item = relationship("InventoryItem", back_populates="transactions")
    performed_by = relationship("User")

    def __repr__(self) -> str:
        return f"<InventoryTransaction {self.transaction_type} {self.quantity} for Item #{self.inventory_item_id}>"
