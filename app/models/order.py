import enum

from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.models.base import TimestampMixin


class OrderPlatform(str, enum.Enum):
    WEBSITE = "WEBSITE"
    ZOMATO = "ZOMATO"
    SWIGGY = "SWIGGY"


class OrderStatus(str, enum.Enum):
    NEW = "NEW"
    CONFIRMED = "CONFIRMED"
    PREPARING = "PREPARING"
    READY = "READY"
    OUT_FOR_DELIVERY = "OUT_FOR_DELIVERY"
    DELIVERED = "DELIVERED"
    CANCELLED = "CANCELLED"


class PaymentStatus(str, enum.Enum):
    PENDING = "PENDING"
    PAID = "PAID"
    FAILED = "FAILED"
    REFUNDED = "REFUNDED"


class Order(Base, TimestampMixin):
    __tablename__ = "orders"

    order_number = Column(String(50), unique=True, index=True, nullable=False)
    platform = Column(String(50), default=OrderPlatform.WEBSITE.value, index=True, nullable=False)
    customer_id = Column(Integer, ForeignKey("customers.id", ondelete="SET NULL"), nullable=True, index=True)
    customer_name = Column(String(255), nullable=False)
    customer_phone = Column(String(50), nullable=False)
    delivery_address = Column(Text, nullable=True)

    subtotal = Column(Float, default=0.0, nullable=False)
    discount = Column(Float, default=0.0, nullable=False)
    delivery_fee = Column(Float, default=0.0, nullable=False)
    tax = Column(Float, default=0.0, nullable=False)
    total_amount = Column(Float, default=0.0, nullable=False)
    # Online-payment surcharges & notification fee (VAS) recorded per order.
    transaction_fee = Column(Float, default=0.0, nullable=False)
    vas_fee = Column(Float, default=0.0, nullable=False)
    other_expense = Column(Float, default=0.0, nullable=False)  # snapshot, margin only (not charged)
    # Gateway reference used to issue refunds (e.g. Razorpay payment_id).
    gateway = Column(String(50), nullable=True)
    order_type = Column(String(20), nullable=True)  # DELIVERY / PICKUP
    gateway_payment_id = Column(String(100), nullable=True, index=True)
    gateway_order_id = Column(String(100), nullable=True)
    # Structured refund data (surfaced in the CRM order detail).
    refund_id = Column(String(100), nullable=True)
    refund_amount = Column(Float, nullable=True)
    refunded_at = Column(DateTime, nullable=True)

    order_status = Column(String(50), default=OrderStatus.NEW.value, index=True, nullable=False)
    payment_status = Column(String(50), default=PaymentStatus.PAID.value, index=True, nullable=False)
    items_summary = Column(String(500), nullable=True)
    notes = Column(String(500), nullable=True)

    # Relationships
    customer = relationship("Customer", back_populates="orders")
    items = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")
    status_history = relationship(
        "OrderStatusHistory",
        back_populates="order",
        cascade="all, delete-orphan",
        order_by="desc(OrderStatusHistory.created_at)",
    )

    def __repr__(self) -> str:
        return f"<Order {self.order_number} ({self.platform}: {self.order_status})>"


class OrderItem(Base, TimestampMixin):
    __tablename__ = "order_items"

    order_id = Column(Integer, ForeignKey("orders.id", ondelete="CASCADE"), nullable=False, index=True)
    item_name = Column(String(255), nullable=False)
    portion_size = Column(String(50), default="500g", nullable=False)
    quantity = Column(Integer, default=1, nullable=False)
    unit_price = Column(Float, default=0.0, nullable=False)
    total_price = Column(Float, default=0.0, nullable=False)
    cost_price = Column(Float, default=0.0, nullable=False)  # food cost snapshot (per unit)
    is_free = Column(Boolean, default=False, nullable=False)

    order = relationship("Order", back_populates="items")
