from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class WebsiteOrderItemInput(BaseModel):
    item_name: str = Field(..., min_length=2, max_length=150, description="Name of the biryani or item")
    portion_size: str = Field("500g", max_length=50, description="Portion size: 250g, 500g, 750g, 1kg, Single")
    quantity: int = Field(1, ge=1, le=50, description="Quantity of items")
    unit_price: float = Field(..., ge=0.0, description="Unit price in INR")
    notes: str | None = Field(None, max_length=250, description="Customization notes like extra raita")
    is_free: bool = Field(False, description="True when this line item is a complimentary promo gift")


class WebsiteCustomerInput(BaseModel):
    name: str = Field(..., min_length=2, max_length=150, description="Customer full name")
    phone: str = Field(..., min_length=10, max_length=20, description="10-digit mobile number")
    email: str | None = Field(None, max_length=150, description="Optional customer email")
    delivery_address: str = Field(..., min_length=5, max_length=500, description="Delivery street and flat address")


class WebsiteOrderCreateRequest(BaseModel):
    customer: WebsiteCustomerInput
    items: list[WebsiteOrderItemInput] = Field(..., min_length=1, description="Order must contain at least 1 item")
    payment_method: str = Field("COD", description="Payment method: COD, ONLINE_UPI, CARD")
    delivery_fee: float = Field(0.0, ge=0.0)
    discount: float = Field(0.0, ge=0.0)
    discount_type: str | None = Field(None, description="Promo discount type: fixed, percentage, free_item, free_delivery")
    free_item_name: str | None = Field(None, description="Name of the complimentary free item from promo code")
    tax: float = Field(0.0, ge=0.0, description="Tax amount already included in the website order total")
    notes: str | None = Field(None, max_length=500, description="Special cooking or delivery instructions")


class WebsiteOrderCreateResponse(BaseModel):
    order_number: str
    order_status: str
    payment_status: str
    subtotal: float
    discount: float
    delivery_fee: float
    tax: float
    total_amount: float
    estimated_delivery_minutes: int
    tracking_token: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TrackingTimelineStep(BaseModel):
    step_key: str
    label: str
    description: str
    completed: bool
    current: bool
    timestamp: datetime | None = None


class PublicOrderTrackResponse(BaseModel):
    order_number: str
    order_status: str
    status_display: str
    payment_status: str
    customer_name: str
    customer_phone_masked: str
    delivery_address: str
    items_summary: str
    items_count: int
    total_amount: float
    created_at: datetime
    estimated_delivery_minutes: int
    timeline: list[TrackingTimelineStep]

    model_config = ConfigDict(from_attributes=True)


class PaymentWebhookRequest(BaseModel):
    payment_status: str = Field(..., description="PAID, FAILED, PENDING, REFUNDED")
    transaction_id: str | None = Field(None, description="Gateway transaction or reference ID")
    payment_gateway: str | None = Field("RAZORPAY", description="Payment gateway name")
    notes: str | None = Field(None, description="Gateway callback response notes")


class PaymentWebhookResponse(BaseModel):
    success: bool
    order_number: str
    previous_payment_status: str
    new_payment_status: str
    order_status: str
    message: str
