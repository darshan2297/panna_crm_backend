from sqlalchemy import Boolean, Column, Float, Integer, String, Text

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
