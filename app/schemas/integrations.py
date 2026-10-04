from datetime import datetime

from pydantic import BaseModel


class IntegrationConfigRead(BaseModel):
    id: int
    platform: str
    is_enabled: bool
    store_id: str | None = None
    api_key_masked: str | None = None
    auto_accept: bool
    environment: str
    status: str
    last_sync_at: datetime | None = None
    orders_synced_today: int
    sync_interval_minutes: int
    shop_open: bool = True
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class IntegrationConfigUpdate(BaseModel):
    is_enabled: bool | None = None
    store_id: str | None = None
    api_key: str | None = None
    webhook_secret: str | None = None
    auto_accept: bool | None = None
    environment: str | None = None
    sync_interval_minutes: int | None = None
    shop_open: bool | None = None


class IntegrationLogRead(BaseModel):
    id: int
    platform: str
    event_type: str
    status: str
    payload_snippet: str | None = None
    message: str | None = None
    created_at: datetime

    class Config:
        from_attributes = True


class WebhookSimulateItem(BaseModel):
    item_name: str
    quantity: int = 1
    unit_price: float = 300.0


class WebhookSimulateRequest(BaseModel):
    platform: str  # ZOMATO or SWIGGY
    event_type: str = "ORDER_PLACED"  # ORDER_PLACED, ORDER_CANCELLED, RIDER_ASSIGNED, DELIVERED
    customer_name: str | None = "Priya Sharma"
    customer_phone: str | None = "9876543210"
    delivery_address: str | None = "Flat 402, Royal Palms, Pune"
    items: list[WebhookSimulateItem] | None = None
    total_amount: float | None = None


class IntegrationHealthSummary(BaseModel):
    platforms: list[IntegrationConfigRead]
    overall_status: str
    total_synced_today: int
    active_platforms_count: int
