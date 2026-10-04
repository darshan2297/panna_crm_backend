from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


# --- Portion Schemas ---
class MenuItemPortionBase(BaseModel):
    portion_size: str = Field(
        ..., min_length=1, max_length=50, description="Portion name: Single, 250g, 500g, 750g, 1kg"
    )
    weight_grams: int | None = Field(None, ge=1, description="Weight in grams if applicable")
    serves_persons: str | None = Field(None, max_length=50, description="e.g. 1-2 Persons")
    cost_price: float = Field(0.0, ge=0.0, description="Internal food cost in INR")
    base_price: float = Field(..., ge=0.0, description="Selling price on direct website / dine-in")
    zomato_price: float | None = Field(None, ge=0.0, description="Selling price on Zomato (+22% default markup)")
    swiggy_price: float | None = Field(None, ge=0.0, description="Selling price on Swiggy (+20% default markup)")
    is_available: bool = Field(True, description="Availability toggle for this portion")


class MenuItemPortionCreate(MenuItemPortionBase):
    pass


class MenuItemPortionUpdate(BaseModel):
    id: int | None = None
    portion_size: str | None = None
    weight_grams: int | None = None
    serves_persons: str | None = None
    cost_price: float | None = None
    base_price: float | None = None
    zomato_price: float | None = None
    swiggy_price: float | None = None
    is_available: bool | None = None


class MenuItemPortionResponse(MenuItemPortionBase):
    id: int
    menu_item_id: int
    profit_margin_percent: float = 0.0
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# --- Category Schemas ---
class MenuCategoryBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    description: str | None = Field(None, max_length=500)
    display_order: int = Field(0, ge=0)
    is_active: bool = Field(True)


class MenuCategoryCreate(MenuCategoryBase):
    pass


class MenuCategoryUpdate(BaseModel):
    name: str | None = Field(None, min_length=2, max_length=100)
    description: str | None = None
    display_order: int | None = Field(None, ge=0)
    is_active: bool | None = None


class MenuCategoryResponse(MenuCategoryBase):
    id: int
    slug: str
    items_count: int = 0
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# --- Menu Item Schemas ---
class MenuItemBase(BaseModel):
    category_id: int
    name: str = Field(..., min_length=2, max_length=150)
    description: str | None = Field(None, max_length=1000)
    is_veg: bool = Field(False)
    spice_level: str = Field("MEDIUM", description="MILD, MEDIUM, SPICY, EXTRA_SPICY")
    preparation_time_minutes: int = Field(25, ge=5, le=120)
    image_url: str | None = Field(None, max_length=500)
    is_available: bool = Field(True, description="In Stock toggle")
    is_active: bool = Field(True, description="Published toggle")
    display_order: int = Field(0, ge=0)


class MenuItemCreate(MenuItemBase):
    portions: list[MenuItemPortionCreate] = Field(..., min_length=1, description="Item must have at least one portion")


class MenuItemUpdate(BaseModel):
    category_id: int | None = None
    name: str | None = Field(None, min_length=2, max_length=150)
    description: str | None = None
    is_veg: bool | None = None
    spice_level: str | None = None
    preparation_time_minutes: int | None = None
    image_url: str | None = None
    is_available: bool | None = None
    is_active: bool | None = None
    display_order: int | None = None
    portions: list[MenuItemPortionUpdate] | None = None


class MenuItemAvailabilityUpdate(BaseModel):
    is_available: bool = Field(..., description="Set In Stock (True) or Out of Stock (False)")


class MenuItemResponse(MenuItemBase):
    id: int
    slug: str
    category_name: str
    starting_price: float
    portions: list[MenuItemPortionResponse] = []
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class MenuCategoryDetailResponse(MenuCategoryResponse):
    items: list[MenuItemResponse] = []


class MenuSummaryResponse(BaseModel):
    total_items: int
    total_categories: int
    veg_items_count: int
    non_veg_items_count: int
    available_items_count: int
    out_of_stock_count: int


# Price Calculation Helper
class PlatformPriceCalculationRequest(BaseModel):
    base_price: float = Field(..., ge=0.0)


class PlatformPriceCalculationResponse(BaseModel):
    base_price: float
    website_price: float
    zomato_price: float
    swiggy_price: float
    zomato_markup_percent: float = 22.0
    swiggy_markup_percent: float = 20.0
