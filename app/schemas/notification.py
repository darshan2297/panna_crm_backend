from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class NotificationBase(BaseModel):
    title: str = Field(..., max_length=255)
    message: str
    type: str = "LOW_STOCK"  # LOW_STOCK, CRITICAL_STOCK, OUT_OF_STOCK, RESTOCK_PO, ORDER_ALERT, SYSTEM
    severity: str = "WARNING"  # INFO, WARNING, CRITICAL, SUCCESS
    entity_type: str | None = None
    entity_id: int | None = None
    channel: str = "IN_APP"
    recipient: str | None = None
    metadata_json: str | None = None


class NotificationCreate(NotificationBase):
    pass


class NotificationOut(NotificationBase):
    id: int
    is_read: bool
    channel_status: str
    created_at: datetime
    read_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class NotificationSummary(BaseModel):
    total_notifications: int
    unread_count: int
    critical_count: int
    warning_count: int
    stock_alert_count: int
    order_alert_count: int


class NotificationDispatchInput(BaseModel):
    channel: str = Field("WHATSAPP", description="WHATSAPP or EMAIL")
    recipient: str | None = Field(None, description="Phone number with country code for WhatsApp, or Email address")
    custom_message: str | None = None


class NotificationDispatchResult(BaseModel):
    notification_id: int
    channel: str
    recipient: str
    status: str
    preview_content: str
    action_url: str | None = None  # e.g. wa.me link or mailto link
    dispatched_at: datetime
