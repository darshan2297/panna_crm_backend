from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.order import OrderPlatform, OrderStatus, PaymentStatus


class OrderItemBase(BaseModel):
    item_name: str = Field(..., min_length=1, max_length=255)
    portion_size: str = Field(default="500g", max_length=50)
    quantity: int = Field(default=1, ge=1)
    unit_price: float = Field(..., ge=0.0)


class OrderItemCreate(OrderItemBase):
    pass


class OrderItemResponse(OrderItemBase):
    id: int
    order_id: int
    total_price: float
    cost_price: float = 0.0
    is_free: bool = False
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class OrderStatusHistoryResponse(BaseModel):
    id: int
    order_id: int
    previous_status: str | None = None
    new_status: str
    changed_by_name: str
    notes: str | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CustomerBriefResponse(BaseModel):
    id: int
    name: str
    phone: str
    email: str | None = None
    default_address: str | None = None
    total_orders: int
    total_spent: float

    model_config = ConfigDict(from_attributes=True)


class OrderCreate(BaseModel):
    platform: OrderPlatform = Field(default=OrderPlatform.WEBSITE)
    customer_name: str = Field(..., min_length=2, max_length=255)
    customer_phone: str = Field(..., min_length=7, max_length=50)
    customer_email: str | None = None
    delivery_address: str | None = None
    items: list[OrderItemCreate] = Field(..., min_length=1)
    discount: float = Field(default=0.0, ge=0.0)
    delivery_fee: float = Field(default=0.0, ge=0.0)
    payment_status: PaymentStatus = Field(default=PaymentStatus.PAID)
    notes: str | None = None


class OrderUpdateStatus(BaseModel):
    new_status: OrderStatus
    notes: str | None = None


class OrderCancelRequest(BaseModel):
    reason: str = Field(..., min_length=3, max_length=500)


class OrderRefundRequest(BaseModel):
    # None => full refund; otherwise a positive amount in INR (<= order total).
    amount: float | None = Field(None, ge=0)
    reason: str = Field("", max_length=500)


class OrderResponse(BaseModel):
    id: int
    order_number: str
    platform: str
    customer_id: int | None = None
    customer_name: str
    customer_phone: str
    delivery_address: str | None = None
    subtotal: float
    discount: float
    delivery_fee: float
    transaction_fee: float = 0.0
    vas_fee: float = 0.0
    other_expense: float = 0.0
    tax: float
    total_amount: float
    order_status: str
    payment_status: str
    gateway: str | None = None
    gateway_payment_id: str | None = None
    gateway_order_id: str | None = None
    refund_id: str | None = None
    refund_amount: float | None = None
    refunded_at: datetime | None = None
    items_summary: str | None = None
    notes: str | None = None
    created_at: datetime
    updated_at: datetime
    items_count: int = 1

    model_config = ConfigDict(from_attributes=True)


class OrderDetailResponse(OrderResponse):
    items: list[OrderItemResponse] = []
    status_history: list[OrderStatusHistoryResponse] = []
    customer: CustomerBriefResponse | None = None
    platform_display: str = ""
    estimated_commission: float = 0.0
    # Aggregate food cost (sum of item cost_price × qty) for margin reporting.
    food_cost: float = 0.0

    model_config = ConfigDict(from_attributes=True)


class OrderStatusSummary(BaseModel):
    total_orders: int = 0
    new: int = 0
    confirmed: int = 0
    preparing: int = 0
    ready: int = 0
    out_for_delivery: int = 0
    delivered: int = 0
    cancelled: int = 0
    today_orders: int = 0
    today_revenue: float = 0.0
