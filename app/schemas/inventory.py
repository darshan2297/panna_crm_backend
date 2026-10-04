from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class InventoryCategoryEnum(str, Enum):
    GRAIN = "GRAIN"
    MEAT = "MEAT"
    DAIRY = "DAIRY"
    VEGETABLE = "VEGETABLE"
    SPICE = "SPICE"
    OIL = "OIL"
    PACKAGING = "PACKAGING"
    OTHER = "OTHER"


class InventoryTransactionTypeEnum(str, Enum):
    STOCK_IN = "STOCK_IN"
    STOCK_OUT = "STOCK_OUT"
    WASTAGE = "WASTAGE"
    AUDIT_CORRECTION = "AUDIT_CORRECTION"


class InventoryItemBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=255, description="Ingredient or item name")
    sku: str | None = Field(None, max_length=100, description="SKU identifier, auto-generated if blank")
    category: str = Field(default="GRAIN", description="Inventory category")
    unit: str = Field(default="kg", max_length=50, description="Unit of measurement (kg, g, l, ml, pcs, packet)")
    current_stock: float = Field(default=0.0, ge=0.0, description="Current stock level")
    minimum_stock: float = Field(default=10.0, ge=0.0, description="Safety minimum stock threshold")
    reorder_level: float = Field(default=15.0, ge=0.0, description="Threshold triggering reorder alert")
    purchase_price: float = Field(default=0.0, ge=0.0, description="Purchase cost per unit in INR")
    supplier: str | None = Field(None, max_length=255, description="Primary supplier / distributor name")
    storage_location: str | None = Field(None, max_length=255, description="Location in kitchen/store e.g. Cold Room A")
    description: str | None = Field(None, max_length=500, description="Item notes or recipe usage")
    is_active: bool = Field(default=True, description="Active status")


class InventoryItemCreate(InventoryItemBase):
    pass


class InventoryItemUpdate(BaseModel):
    name: str | None = Field(None, min_length=2, max_length=255)
    sku: str | None = Field(None, max_length=100)
    category: str | None = None
    unit: str | None = None
    current_stock: float | None = Field(None, ge=0.0)
    minimum_stock: float | None = Field(None, ge=0.0)
    reorder_level: float | None = Field(None, ge=0.0)
    purchase_price: float | None = Field(None, ge=0.0)
    supplier: str | None = None
    storage_location: str | None = None
    description: str | None = None
    is_active: bool | None = None


class InventoryItemResponse(InventoryItemBase):
    id: int
    is_low_stock: bool = False
    is_critical_stock: bool = False
    total_valuation: float = 0.0
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class InventoryTransactionCreate(BaseModel):
    transaction_type: InventoryTransactionTypeEnum
    quantity: float = Field(..., gt=0.0, description="Transaction quantity (must be positive)")
    unit_price: float | None = Field(None, ge=0.0, description="Cost per unit in INR (defaults to item purchase price)")
    reference_no: str | None = Field(None, max_length=100, description="PO number, batch id, or invoice ref")
    notes: str | None = Field(None, max_length=500, description="Operational notes or reason")


class InventoryTransactionResponse(BaseModel):
    id: int
    inventory_item_id: int
    item_name: str | None = None
    item_sku: str | None = None
    item_unit: str | None = None
    item_category: str | None = None
    transaction_type: str
    quantity: float
    stock_before: float
    stock_after: float
    unit_price: float | None = None
    total_cost: float | None = None
    reference_no: str | None = None
    notes: str | None = None
    performed_by_id: int | None = None
    performed_by_name: str | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class InventoryItemDetailResponse(InventoryItemResponse):
    recent_transactions: list[InventoryTransactionResponse] = []


class CategoryValuation(BaseModel):
    category: str
    item_count: int
    total_valuation: float


class InventorySummaryResponse(BaseModel):
    total_items: int
    in_stock_items: int
    low_stock_items: int
    critical_stock_items: int
    out_of_stock_items: int
    total_inventory_value_inr: float
    category_valuations: list[CategoryValuation]
