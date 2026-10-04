from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class PackagingCategoryEnum(str, Enum):
    CONTAINER = "CONTAINER"
    BAG = "BAG"
    ACCOMPANIMENT = "ACCOMPANIMENT"
    CUTLERY = "CUTLERY"
    SEALING_LABEL = "SEALING_LABEL"
    OTHER = "OTHER"


class PackagingTransactionTypeEnum(str, Enum):
    STOCK_IN = "STOCK_IN"
    STOCK_OUT = "STOCK_OUT"
    WASTAGE = "WASTAGE"
    ORDER_CONSUMPTION = "ORDER_CONSUMPTION"
    AUDIT_CORRECTION = "AUDIT_CORRECTION"


class PackagingItemBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=255, description="Packaging item name (e.g. 500ml Round Biryani Container)")
    sku: str | None = Field(None, max_length=100, description="SKU identifier, auto-generated if blank")
    category: str = Field(default="CONTAINER", description="Packaging category")
    material: str = Field(default="Food Grade PP", max_length=100, description="Material type (Kraft Paper, PP, Clay, Wood, Foil)")
    capacity: str | None = Field(None, max_length=100, description="Capacity or size (500ml, 1kg, 250ml, Standard)")
    unit: str = Field(default="pcs", max_length=50, description="Unit of measurement (pcs, roll, pack)")
    current_stock: float = Field(default=0.0, ge=0.0, description="Current stock in kitchen/store")
    minimum_stock: float = Field(default=50.0, ge=0.0, description="Minimum stock threshold for critical alert")
    reorder_level: float = Field(default=100.0, ge=0.0, description="Stock reorder alert trigger level")
    purchase_cost: float = Field(default=0.0, ge=0.0, description="Purchase cost per unit in INR")
    supplier: str | None = Field(None, max_length=255, description="Packaging supplier/vendor name")
    storage_location: str | None = Field(None, max_length=255, description="Storage rack/cabinet in kitchen")
    description: str | None = Field(None, max_length=500, description="Specifications, food-grade certifications, notes")
    is_active: bool = Field(default=True, description="Active status")


class PackagingItemCreate(PackagingItemBase):
    pass


class PackagingItemUpdate(BaseModel):
    name: str | None = Field(None, min_length=2, max_length=255)
    sku: str | None = Field(None, max_length=100)
    category: str | None = None
    material: str | None = None
    capacity: str | None = None
    unit: str | None = None
    current_stock: float | None = Field(None, ge=0.0)
    minimum_stock: float | None = Field(None, ge=0.0)
    reorder_level: float | None = Field(None, ge=0.0)
    purchase_cost: float | None = Field(None, ge=0.0)
    supplier: str | None = None
    storage_location: str | None = None
    description: str | None = None
    is_active: bool | None = None


class PackagingItemResponse(PackagingItemBase):
    id: int
    is_low_stock: bool = False
    is_critical_stock: bool = False
    total_valuation: float = 0.0
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class PackagingTransactionCreate(BaseModel):
    transaction_type: PackagingTransactionTypeEnum
    quantity: float = Field(..., gt=0.0, description="Transaction quantity (must be positive)")
    unit_cost: float | None = Field(None, ge=0.0, description="Cost per unit in INR (defaults to item purchase cost)")
    order_id: int | None = Field(None, description="Optional associated Order ID")
    reference_no: str | None = Field(None, max_length=100, description="PO number, invoice ref, or order number")
    notes: str | None = Field(None, max_length=500, description="Operational notes or reason")


class PackagingTransactionResponse(BaseModel):
    id: int
    packaging_item_id: int
    item_name: str | None = None
    item_sku: str | None = None
    item_unit: str | None = None
    item_category: str | None = None
    transaction_type: str
    quantity: float
    stock_before: float
    stock_after: float
    unit_cost: float | None = None
    total_cost: float | None = None
    order_id: int | None = None
    reference_no: str | None = None
    notes: str | None = None
    performed_by_id: int | None = None
    performed_by_name: str | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PackagingItemDetailResponse(PackagingItemResponse):
    recent_transactions: list[PackagingTransactionResponse] = []


class PackagingConsumptionRuleBase(BaseModel):
    dish_category: str | None = Field(None, max_length=100, description="Dish category name (e.g., Dum Biryani, Starters & Kebabs, ALL_ORDERS)")
    portion_size: str | None = Field(None, max_length=50, description="Portion size e.g. Single, 250g, 500g, 750g, 1kg, ALL")
    packaging_item_id: int = Field(..., description="ID of packaging item used")
    quantity_per_order_unit: float = Field(default=1.0, gt=0.0, description="Packaging quantity consumed per dish unit")
    description: str | None = Field(None, max_length=255, description="Rule description or packaging instruction")
    is_active: bool = Field(default=True, description="Active status")


class PackagingConsumptionRuleCreate(PackagingConsumptionRuleBase):
    pass


class PackagingConsumptionRuleResponse(PackagingConsumptionRuleBase):
    id: int
    packaging_item_name: str | None = None
    packaging_item_sku: str | None = None
    packaging_item_unit: str | None = None
    packaging_item_cost: float | None = None
    created_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class PackagingOrderSimulationItem(BaseModel):
    dish_category: str = Field(default="Dum Biryani", description="Category of dish ordered")
    portion_size: str | None = Field(default="500g", description="Portion size")
    quantity: int = Field(default=1, ge=1, description="Quantity ordered")


class PackagingOrderSimulationRequest(BaseModel):
    items: list[PackagingOrderSimulationItem] = Field(..., min_length=1)


class PackagingItemConsumptionEstimate(BaseModel):
    packaging_item_id: int
    item_name: str
    item_sku: str
    category: str
    unit: str
    units_consumed: float
    unit_cost: float
    total_cost: float


class PackagingOrderSimulationResponse(BaseModel):
    consumed_items: list[PackagingItemConsumptionEstimate]
    total_packaging_units: float
    total_packaging_cost_inr: float


class CategoryPackagingValuation(BaseModel):
    category: str
    item_count: int
    total_valuation: float


class PackagingSummaryResponse(BaseModel):
    total_items: int
    in_stock_items: int
    low_stock_items: int
    critical_stock_items: int
    out_of_stock_items: int
    total_packaging_value_inr: float
    category_valuations: list[CategoryPackagingValuation]
    daily_consumption_units: float
    daily_consumption_cost_inr: float
