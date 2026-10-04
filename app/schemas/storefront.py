from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class StorefrontConfigResponse(BaseModel):
    id: int
    logo_url: str | None = None
    banner_url: str | None = None
    banner_mobile_url: str | None = None
    gift_section_enabled: bool = True
    gift_bg_url: str | None = None
    bulk_bg_url: str | None = None
    delivery_enabled: bool = True
    pickup_enabled: bool = True
    delivery_fee: float = 49.0
    free_delivery_enabled: bool = True
    free_delivery_threshold: float = 800.0
    brand_name: str | None = None
    brand_tagline: str | None = None
    address_line: str | None = None
    area: str | None = None
    city: str | None = None
    pincode: str | None = None
    google_maps_url: str | None = None
    phone: str | None = None
    whatsapp: str | None = None
    email: str | None = None
    operating_hours: str | None = None

    model_config = ConfigDict(from_attributes=True)


class StorefrontConfigUpdate(BaseModel):
    logo_url: str | None = None
    banner_url: str | None = None
    banner_mobile_url: str | None = None
    gift_section_enabled: bool | None = None
    gift_bg_url: str | None = None
    bulk_bg_url: str | None = None
    delivery_enabled: bool | None = None
    pickup_enabled: bool | None = None
    delivery_fee: float | None = Field(None, ge=0)
    free_delivery_enabled: bool | None = None
    free_delivery_threshold: float | None = Field(None, ge=0)
    brand_name: str | None = None
    brand_tagline: str | None = None
    address_line: str | None = None
    area: str | None = None
    city: str | None = None
    pincode: str | None = None
    google_maps_url: str | None = None
    phone: str | None = None
    whatsapp: str | None = None
    email: str | None = None
    operating_hours: str | None = None


class PaymentMethodResponse(BaseModel):
    id: int
    key: str
    label: str
    description: str | None = None
    enabled: bool
    display_order: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PaymentMethodCreate(BaseModel):
    key: str = Field(..., min_length=2, max_length=50)
    label: str = Field(..., min_length=2, max_length=150)
    description: str | None = None
    enabled: bool = True
    display_order: int = 0


class PaymentMethodUpdate(BaseModel):
    label: str | None = None
    description: str | None = None
    enabled: bool | None = None
    display_order: int | None = None


class PromoCodeCreate(BaseModel):
    code: str = Field(..., min_length=2, max_length=50)
    title: str = Field(..., min_length=2, max_length=150)
    subtitle: str | None = None
    description: str | None = None
    discount_type: str = Field("fixed", description="fixed | percentage | free_item | free_delivery")
    discount_value: float = Field(0.0, ge=0)
    free_item_name: str | None = None
    min_order_value: float = Field(0.0, ge=0)
    badge: str | None = None
    active: bool = True


class PromoCodeUpdate(BaseModel):
    code: str | None = Field(None, min_length=2, max_length=50)
    title: str | None = None
    subtitle: str | None = None
    description: str | None = None
    discount_type: str | None = None
    discount_value: float | None = Field(None, ge=0)
    free_item_name: str | None = None
    min_order_value: float | None = Field(None, ge=0)
    badge: str | None = None
    active: bool | None = None


class PromoCodeResponse(BaseModel):
    id: int
    code: str
    title: str
    subtitle: str | None = None
    description: str | None = None
    discount_type: str
    discount_value: float
    free_item_name: str | None = None
    min_order_value: float
    badge: str | None = None
    active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
