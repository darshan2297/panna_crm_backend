import json
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


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
    valid_from: datetime | None = None
    valid_until: datetime | None = None
    max_uses: int | None = Field(None, ge=0)
    used_count: int = Field(0, ge=0)
    per_user_limit: int = Field(1, ge=0)
    applicable_items: list[str] | None = None
    minimum_order_items: int | None = Field(None, ge=0)


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
    valid_from: datetime | None = None
    valid_until: datetime | None = None
    max_uses: int | None = Field(None, ge=0)
    per_user_limit: int | None = Field(None, ge=0)
    applicable_items: list[str] | None = None
    minimum_order_items: int | None = Field(None, ge=0)


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
    valid_from: datetime | None = None
    valid_until: datetime | None = None
    max_uses: int | None = None
    used_count: int = 0
    per_user_limit: int = 1
    applicable_items: list[str] | None = None
    minimum_order_items: int | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @field_validator("applicable_items", mode="before")
    @classmethod
    def _parse_applicable_items(cls, v):
        if isinstance(v, str):
            try:
                parsed = json.loads(v)
                return parsed if isinstance(parsed, list) else None
            except Exception:
                return None
        return v


class PromoCodeValidateRequest(BaseModel):
    order_value: float = Field(0.0, ge=0)
    item_count: int = Field(0, ge=0)
    cart_item_slugs: list[str] | None = None
    user_uses: int = Field(0, ge=0)


class PromoCodeValidateResult(BaseModel):
    valid: bool
    reason: str | None = None
    code: str | None = None
    discount_type: str | None = None
    discount_value: float | None = None
    min_order_value: float | None = None
