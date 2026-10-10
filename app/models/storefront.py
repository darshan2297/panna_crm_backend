from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.models.base import TimestampMixin


class StorefrontConfig(Base, TimestampMixin):
    """Singleton row (id=1) controlling what the public website renders."""

    __tablename__ = "storefront_config"

    logo_url = Column(String(500), nullable=True)
    banner_url = Column(String(500), nullable=True)
    banner_mobile_url = Column(String(500), nullable=True)

    gift_section_enabled = Column(Boolean, default=True, nullable=False)
    gift_bg_url = Column(String(500), nullable=True)

    bulk_bg_url = Column(String(500), nullable=True)

    delivery_enabled = Column(Boolean, default=True, nullable=False)
    pickup_enabled = Column(Boolean, default=True, nullable=False)
    delivery_fee = Column(Float, default=49.0, nullable=False)

    free_delivery_enabled = Column(Boolean, default=True, nullable=False)
    free_delivery_threshold = Column(Float, default=800.0, nullable=False)

    brand_name = Column(String(150), nullable=True)
    brand_tagline = Column(String(255), nullable=True)
    address_line = Column(String(500), nullable=True)
    area = Column(String(100), nullable=True)
    city = Column(String(100), nullable=True)
    pincode = Column(String(20), nullable=True)
    google_maps_url = Column(String(500), nullable=True)
    phone = Column(String(30), nullable=True)
    whatsapp = Column(String(30), nullable=True)
    email = Column(String(255), nullable=True)
    operating_hours = Column(String(255), nullable=True)

    # Online-payment surcharges & notification fee (VAS).
    #   transaction_fee_percent: % added to ONLINE orders (payment gateway fee)
    #   gst_percent:            GST % added to ONLINE orders only
    #   vas_fee:                flat per-order fee for WhatsApp/SMS/Email
    transaction_fee_percent = Column(Float, default=0.0, nullable=False)
    gst_percent = Column(Float, default=5.0, nullable=False)
    gst_number = Column(String(50), nullable=True)
    vas_fee = Column(Float, default=0.0, nullable=False)
    # Flat per-order "other expenses" component used in the margin formula.
    other_expense = Column(Float, default=0.0, nullable=False)


class PaymentMethodConfig(Base, TimestampMixin):
    __tablename__ = "payment_method_configs"

    key = Column(String(50), nullable=False, unique=True, index=True)  # e.g. "online", "cod"
    label = Column(String(150), nullable=False)
    description = Column(String(255), nullable=True)
    enabled = Column(Boolean, default=True, nullable=False)
    display_order = Column(Integer, default=0, nullable=False)


class PromoCode(Base, TimestampMixin):
    __tablename__ = "promocodes"

    code = Column(String(50), nullable=False, unique=True, index=True)
    title = Column(String(150), nullable=False)
    subtitle = Column(String(255), nullable=True)
    description = Column(Text, nullable=True)
    discount_type = Column(String(30), nullable=False, default="fixed")  # fixed | percentage | free_item | free_delivery
    discount_value = Column(Float, default=0.0, nullable=False)
    free_item_name = Column(String(150), nullable=True)
    min_order_value = Column(Float, default=0.0, nullable=False)
    badge = Column(String(100), nullable=True)
    active = Column(Boolean, default=True, nullable=False, index=True)

    valid_from = Column(DateTime, nullable=True)
    valid_until = Column(DateTime, nullable=True)
    max_uses = Column(Integer, nullable=True)
    used_count = Column(Integer, default=0, nullable=False)
    per_user_limit = Column(Integer, default=1, nullable=False)
    applicable_items = Column(Text, nullable=True)  # JSON list of item slugs/categories
    minimum_order_items = Column(Integer, nullable=True)
    first_order_only = Column(Boolean, default=False, nullable=False)

    # --- Advanced discount configuration ---
    # general | single_event | multiple_event
    category = Column(String(30), nullable=False, default="general", index=True)
    # Private codes are redeemable but never listed on the public storefront.
    is_private = Column(Boolean, default=False, nullable=False)
    terms_conditions = Column(Text, nullable=True)
    # "amount" => thresholds read min_order_value/max_order_value
    # "quantity" => thresholds read min_quantity/max_quantity
    discount_on = Column(String(20), nullable=False, default="amount")
    min_quantity = Column(Integer, nullable=True)
    max_quantity = Column(Integer, nullable=True)
    # Upper cart value eligible for the discount (None = no cap)
    max_order_value = Column(Float, nullable=True)
    # Gate to a customer segment / new-vs-returning behaviour
    customer_type = Column(String(30), nullable=False, default="all")  # all | new | returning
    # Caps the rupee value a percentage discount can reach, so a large cart
    # cannot produce an outsized discount. None = uncapped.
    max_discount_amount = Column(Float, nullable=True)

    events = relationship(
        "PromoEvent",
        back_populates="promo_code",
        cascade="all, delete-orphan",
        order_by="PromoEvent.start_date",
    )
    usages = relationship(
        "PromoCodeUsage",
        back_populates="promo_code",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<PromoCode {self.code} ({self.discount_type})>"


class PromoEvent(Base, TimestampMixin):
    """A named campaign window. A promo is valid during ANY of its events."""

    __tablename__ = "promo_events"

    promo_code_id = Column(
        Integer,
        ForeignKey("promocodes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    event_title = Column(String(150), nullable=False)
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime, nullable=False)

    promo_code = relationship("PromoCode", back_populates="events")

    def __repr__(self) -> str:
        return f"<PromoEvent {self.event_title} ({self.start_date} -> {self.end_date})>"


class PromoCodeUsage(Base, TimestampMixin):
    """Per-customer redemption log — backs `per_user_limit` enforcement."""

    __tablename__ = "promo_code_usages"

    promo_code_id = Column(
        Integer,
        ForeignKey("promocodes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # Last 10 digits only, so "+91 9876543210" and "9876543210" collapse together.
    customer_phone = Column(String(10), nullable=False, index=True)
    order_id = Column(Integer, ForeignKey("orders.id", ondelete="SET NULL"), nullable=True)

    promo_code = relationship("PromoCode", back_populates="usages")

    def __repr__(self) -> str:
        return f"<PromoCodeUsage promo={self.promo_code_id} phone={self.customer_phone}>"
