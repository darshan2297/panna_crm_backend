import json
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


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
    transaction_fee_percent: float = 0.0
    gst_percent: float = 5.0
    gst_number: str | None = None
    vas_fee: float = 0.0
    other_expense: float = 0.0

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
    transaction_fee_percent: float | None = Field(None, ge=0, le=100)
    gst_percent: float | None = Field(None, ge=0, le=100)
    gst_number: str | None = Field(None, max_length=50)
    vas_fee: float | None = Field(None, ge=0)
    other_expense: float | None = Field(None, ge=0)


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


class PromoEventInput(BaseModel):
    id: int | None = None
    event_title: str = Field(..., min_length=1, max_length=150)
    start_date: datetime
    end_date: datetime


class PromoCodeBase(BaseModel):
    code: str = Field(..., min_length=2, max_length=50)
    title: str = Field(..., min_length=2, max_length=150)
    subtitle: str | None = None
    description: str | None = None
    discount_type: str = Field("fixed", description="fixed | percentage | free_item | free_delivery")
    discount_value: float = Field(0.0, ge=0)
    free_item_name: str | None = None
    min_order_value: float = Field(0.0, ge=0, description="Minimum cart value; used when discount_on='amount'")
    badge: str | None = None
    active: bool = True
    valid_from: datetime | None = None
    valid_until: datetime | None = None
    max_uses: int | None = Field(None, ge=0)
    per_user_limit: int = Field(1, ge=0, description="Max redemptions per customer")
    applicable_items: list[str] | None = None
    minimum_order_items: int | None = Field(None, ge=0)

    # --- Advanced ---
    category: str = Field("general", description="general | single_event | multiple_event")
    is_private: bool = Field(False, description="Redeemable but hidden from public listings")
    terms_conditions: str | None = None
    discount_on: str = Field("amount", description="amount | quantity")
    min_quantity: int | None = Field(None, ge=0)
    max_quantity: int | None = Field(None, ge=0)
    max_order_value: float | None = Field(None, ge=0)
    customer_type: str = Field("all", description="all | new | returning")
    max_discount_amount: float | None = Field(
        None, ge=0, description="Caps the rupee value a percentage discount can reach"
    )
    events: list[PromoEventInput] | None = None

    @model_validator(mode="after")
    def _check_thresholds(self) -> "PromoCodeBase":
        if self.discount_on == "amount" and self.max_order_value is not None:
            if self.max_order_value < self.min_order_value:
                raise ValueError("Maximum order value cannot be lower than the minimum order value")
        if self.discount_on == "quantity" and self.min_quantity is not None and self.max_quantity is not None:
            if self.max_quantity < self.min_quantity:
                raise ValueError("Maximum quantity cannot be lower than the minimum quantity")
        if self.category == "multiple_event" and (self.events is None or len(self.events) < 2):
            raise ValueError("Multiple event discounts require at least 2 events")
        if self.category == "single_event" and (self.events is None or len(self.events) < 1):
            raise ValueError("Single event discounts require at least 1 event")
        if self.discount_type == "percentage":
            if self.discount_value > 100:
                raise ValueError("Percentage discount cannot exceed 100")
        if self.max_discount_amount is not None and self.max_discount_amount <= 0:
            raise ValueError("Maximum discount amount must be greater than zero")
        return self

    @field_validator("valid_until")
    @classmethod
    def _check_valid_until(cls, v, info):
        start = info.data.get("valid_from")
        if v and start and v <= start:
            raise ValueError("End date must be after the start date")
        return v


class PromoCodeCreate(PromoCodeBase):
    used_count: int = Field(0, ge=0)


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
    category: str | None = None
    is_private: bool | None = None
    terms_conditions: str | None = None
    discount_on: str | None = None
    min_quantity: int | None = Field(None, ge=0)
    max_quantity: int | None = Field(None, ge=0)
    max_order_value: float | None = Field(None, ge=0)
    customer_type: str | None = None
    max_discount_amount: float | None = Field(None, ge=0)
    events: list[PromoEventInput] | None = None


class PromoEventResponse(BaseModel):
    id: int
    event_title: str
    start_date: datetime
    end_date: datetime

    model_config = ConfigDict(from_attributes=True)


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
    first_order_only: bool = False
    category: str = "general"
    is_private: bool = False
    terms_conditions: str | None = None
    discount_on: str = "amount"
    min_quantity: int | None = None
    max_quantity: int | None = None
    max_order_value: float | None = None
    customer_type: str = "all"
    max_discount_amount: float | None = None
    events: list[PromoEventResponse] = Field(default_factory=list)
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
    # Retained for API compatibility; per-user limits are now resolved from the
    # promo_code_usages table keyed on customer_phone.
    user_uses: int = Field(0, ge=0)
    customer_phone: str | None = None


class PromoRedemptionRequest(BaseModel):
    customer_phone: str = Field(..., min_length=10, max_length=20)
    order_id: int | None = None


class PromoCodeValidateResult(BaseModel):
    valid: bool
    reason: str | None = None
    code: str | None = None
    discount_type: str | None = None
    discount_value: float | None = None
    free_item_name: str | None = None
    min_order_value: float | None = None
