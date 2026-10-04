from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class CustomerSummary(BaseModel):
    total_customers: int = 0
    new_customers: int = 0
    vip_customers: int = 0
    regular_customers: int = 0
    lapsed_customers: int = 0
    total_revenue: float = 0.0
    average_order_value: float = 0.0


class CustomerNoteCreate(BaseModel):
    note: str = Field(..., min_length=1, max_length=1000)


class CustomerUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=255)
    email: str | None = Field(None)
    default_address: str | None = Field(None)
    notes: str | None = Field(None)


class CustomerOrderBrief(BaseModel):
    id: int
    order_number: str
    platform: str
    order_status: str
    total_amount: float
    items_summary: str | None = None
    items_count: int = 1
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CustomerResponse(BaseModel):
    id: int
    name: str
    phone: str
    email: str | None = None
    default_address: str | None = None
    total_orders: int
    total_spent: float
    average_order_value: float
    segment: str
    notes: str | None = None
    last_order_date: datetime | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @classmethod
    def from_orm_with_avg(cls, obj) -> "CustomerResponse":
        data = {
            "id": obj.id,
            "name": obj.name,
            "phone": obj.phone,
            "email": obj.email,
            "default_address": obj.default_address,
            "total_orders": obj.total_orders,
            "total_spent": obj.total_spent,
            "average_order_value": obj.average_order_value,
            "segment": obj.segment,
            "notes": obj.notes,
            "last_order_date": obj.last_order_date,
            "created_at": obj.created_at,
            "updated_at": obj.updated_at,
        }
        return cls(**data)


class CustomerDetailResponse(CustomerResponse):
    recent_orders: list[CustomerOrderBrief] = []
    preferred_platform: str | None = None
    preferred_item: str | None = None

    model_config = ConfigDict(from_attributes=True)
