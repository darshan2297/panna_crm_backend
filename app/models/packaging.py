import enum
from datetime import UTC, datetime

from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.models.base import TimestampMixin


class PackagingCategory(str, enum.Enum):
    CONTAINER = "CONTAINER"          # Bowls, Handis, Boxes, Meal Trays
    BAG = "BAG"                      # Kraft Carry Bags, Non-Woven Bags
    ACCOMPANIMENT = "ACCOMPANIMENT"  # Raita Cups, Salan Gravy Pouches, Sweet Cups
    CUTLERY = "CUTLERY"              # Wooden Cutlery Kits, Spoons, Napkins
    SEALING_LABEL = "SEALING_LABEL"  # Tamper Tape, Foil Rolls, Thermal Labels
    OTHER = "OTHER"


class PackagingTransactionType(str, enum.Enum):
    STOCK_IN = "STOCK_IN"
    STOCK_OUT = "STOCK_OUT"
    WASTAGE = "WASTAGE"
    ORDER_CONSUMPTION = "ORDER_CONSUMPTION"
    AUDIT_CORRECTION = "AUDIT_CORRECTION"


class PackagingItem(Base, TimestampMixin):
    __tablename__ = "packaging_items"

    name = Column(String(255), unique=True, index=True, nullable=False)
    sku = Column(String(100), unique=True, index=True, nullable=False)
    category = Column(String(50), default="CONTAINER", nullable=False)
    material = Column(String(100), default="Food Grade PP", nullable=False)  # PP, Kraft, Clay, Wood, Foil
    capacity = Column(String(100), nullable=True)  # 500ml, 1kg, 250ml, 50ml, Standard
    unit = Column(String(50), default="pcs", nullable=False)  # pcs, roll, pack
    current_stock = Column(Float, default=0.0, nullable=False)
    minimum_stock = Column(Float, default=50.0, nullable=False)
    reorder_level = Column(Float, default=100.0, nullable=False)
    purchase_cost = Column(Float, default=0.0, nullable=False)  # ₹ per unit
    supplier = Column(String(255), nullable=True)
    storage_location = Column(String(255), nullable=True)
    description = Column(String(500), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)

    transactions = relationship(
        "PackagingTransaction",
        back_populates="item",
        cascade="all, delete-orphan",
        order_by="desc(PackagingTransaction.created_at)",
    )
    consumption_rules = relationship(
        "PackagingConsumptionRule",
        back_populates="packaging_item",
        cascade="all, delete-orphan",
    )

    @property
    def is_low_stock(self) -> bool:
        return self.current_stock <= self.reorder_level

    @property
    def is_critical_stock(self) -> bool:
        return self.current_stock <= self.minimum_stock

    @property
    def total_valuation(self) -> float:
        return round(self.current_stock * self.purchase_cost, 2)

    def __repr__(self) -> str:
        return f"<PackagingItem {self.name}: {self.current_stock}{self.unit}>"


class PackagingTransaction(Base):
    __tablename__ = "packaging_transactions"

    id = Column(Integer, primary_key=True, index=True)
    packaging_item_id = Column(Integer, ForeignKey("packaging_items.id", ondelete="CASCADE"), nullable=False, index=True)
    transaction_type = Column(String(50), nullable=False, index=True)
    quantity = Column(Float, nullable=False)
    stock_before = Column(Float, nullable=False)
    stock_after = Column(Float, nullable=False)
    unit_cost = Column(Float, nullable=True)
    total_cost = Column(Float, nullable=True)
    order_id = Column(Integer, ForeignKey("orders.id", ondelete="SET NULL"), nullable=True, index=True)
    reference_no = Column(String(100), nullable=True)
    notes = Column(Text, nullable=True)
    performed_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)

    item = relationship("PackagingItem", back_populates="transactions")
    performed_by = relationship("User")

    def __repr__(self) -> str:
        return f"<PackagingTransaction {self.transaction_type} {self.quantity} on Item #{self.packaging_item_id}>"


class PackagingConsumptionRule(Base, TimestampMixin):
    __tablename__ = "packaging_consumption_rules"

    id = Column(Integer, primary_key=True, index=True)
    dish_category = Column(String(100), nullable=True)  # Dum Biryani, Starters & Kebabs, Curries & Gravies, Desserts, Beverages, ALL_ORDERS
    portion_size = Column(String(50), nullable=True)   # Single, 250g, 500g, 750g, 1kg, ALL
    packaging_item_id = Column(Integer, ForeignKey("packaging_items.id", ondelete="CASCADE"), nullable=False, index=True)
    quantity_per_order_unit = Column(Float, default=1.0, nullable=False)
    description = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)

    packaging_item = relationship("PackagingItem", back_populates="consumption_rules")

    def __repr__(self) -> str:
        return f"<PackagingConsumptionRule {self.dish_category} ({self.portion_size}) -> {self.quantity_per_order_unit} of Item #{self.packaging_item_id}>"
