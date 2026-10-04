from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class RestockOrderItemCreate(BaseModel):
    item_type: str = Field("INVENTORY", description="INVENTORY or PACKAGING")
    item_id: int
    ordered_quantity: float = Field(..., gt=0)
    unit_cost: float | None = Field(None, ge=0)


class RestockOrderCreate(BaseModel):
    supplier_name: str = Field(..., max_length=255)
    supplier_contact: str | None = None
    target_type: str = Field("INVENTORY", description="INVENTORY, PACKAGING, or MIXED")
    notes: str | None = None
    created_by_name: str | None = "Kitchen Manager"
    items: list[RestockOrderItemCreate] = Field(..., min_length=1)


class RestockOrderItemOut(BaseModel):
    id: int
    restock_order_id: int
    item_type: str
    item_id: int
    item_name: str
    item_sku: str
    unit: str
    current_stock: float
    reorder_threshold: float
    suggested_quantity: float
    ordered_quantity: float
    unit_cost: float
    total_cost: float
    is_received: bool

    model_config = ConfigDict(from_attributes=True)


class RestockOrderOut(BaseModel):
    id: int
    po_number: str
    supplier_name: str
    supplier_contact: str | None = None
    status: str  # DRAFT, ORDERED, RECEIVED, CANCELLED
    target_type: str
    total_estimated_cost: float
    notes: str | None = None
    created_by_name: str
    ordered_at: datetime | None = None
    received_at: datetime | None = None
    created_at: datetime
    items: list[RestockOrderItemOut] = []

    model_config = ConfigDict(from_attributes=True)


class RestockSuggestionItem(BaseModel):
    item_type: str  # INVENTORY or PACKAGING
    item_id: int
    name: str
    sku: str
    category: str
    unit: str
    current_stock: float
    minimum_stock: float
    reorder_level: float
    purchase_cost: float
    suggested_order_qty: float
    estimated_cost: float
    supplier: str | None = None
    status: str  # OUT_OF_STOCK, CRITICAL, LOW_STOCK


class RestockSummary(BaseModel):
    total_deficit_items: int
    critical_items_count: int
    low_stock_items_count: int
    estimated_restock_investment_inr: float
    open_pos_count: int
    received_pos_count: int
