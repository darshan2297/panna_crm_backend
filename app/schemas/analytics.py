from pydantic import BaseModel


class SalesTrendItem(BaseModel):
    date: str
    day: str
    total_revenue: float
    website_revenue: float
    zomato_revenue: float
    swiggy_revenue: float
    order_count: int
    avg_order_value: float


class SalesTrendResponse(BaseModel):
    items: list[SalesTrendItem]
    total_period_revenue: float
    total_period_orders: int
    average_order_value: float


class TopItemMetric(BaseModel):
    item_id: int
    item_name: str
    category_name: str
    quantity_sold: int
    total_revenue: float
    percentage_of_total: float


class TopItemsResponse(BaseModel):
    items: list[TopItemMetric]
    total_items_sold: int
    total_revenue: float


class PlatformBreakdownMetric(BaseModel):
    platform: str
    display_name: str
    revenue: float
    order_count: int
    avg_order_value: float
    revenue_share_pct: float
    commission_rate_pct: float
    commission_amount: float
    net_revenue: float


class PlatformBreakdownResponse(BaseModel):
    platforms: list[PlatformBreakdownMetric]
    total_gross_revenue: float
    total_commission: float
    total_net_revenue: float


class HourlyVelocityCell(BaseModel):
    day_of_week: int  # 0 = Monday, 6 = Sunday
    day_name: str
    hour: int  # 0 to 23
    order_count: int
    revenue: float


class OrderVelocityResponse(BaseModel):
    cells: list[HourlyVelocityCell]
    peak_hour: int
    peak_day: str
    max_orders_in_slot: int
    total_orders_analyzed: int


class CustomerSegmentMetric(BaseModel):
    segment: str
    customer_count: int
    percentage: float
    total_spent: float
    avg_spent_per_customer: float


class CustomerSegmentsResponse(BaseModel):
    segments: list[CustomerSegmentMetric]
    total_customers: int
    total_revenue: float


class DishMarginMetric(BaseModel):
    item_id: int
    item_name: str
    category_name: str
    selling_price: float
    food_cost: float
    packaging_cost: float
    avg_commission: float
    net_margin_amount: float
    gross_margin_pct: float
    is_low_margin: bool


class DishCostingResponse(BaseModel):
    dishes: list[DishMarginMetric]
    avg_kitchen_margin_pct: float
    low_margin_count: int


class PLSummaryResponse(BaseModel):
    gross_revenue: float
    ingredient_food_cost: float
    packaging_cost: float
    platform_commissions: float
    total_cogs: float
    gross_profit: float
    gross_profit_margin_pct: float
    orders_count: int
