"""DeliveryArea schemas for storefront delivery zones."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class DeliveryAreaCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    pincode: str = Field(..., min_length=1, max_length=20)
    delivery_fee: float = Field(0.0, ge=0)
    estimated_minutes: int = Field(45, ge=1, le=180)
    min_order: float = Field(0.0, ge=0)
    is_active: bool = True
    sort_order: int = 0


class DeliveryAreaUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=255)
    pincode: str | None = Field(None, min_length=1, max_length=20)
    delivery_fee: float | None = Field(None, ge=0)
    estimated_minutes: int | None = Field(None, ge=1, le=180)
    min_order: float | None = Field(None, ge=0)
    is_active: bool | None = None
    sort_order: int | None = None


class DeliveryAreaResponse(BaseModel):
    id: int
    name: str
    pincode: str
    delivery_fee: float
    estimated_minutes: int
    min_order: float
    is_active: bool
    sort_order: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
