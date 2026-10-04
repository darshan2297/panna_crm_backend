from datetime import datetime

from pydantic import BaseModel


class KPIStats(BaseModel):
    total_orders: int
    orders_growth_pct: float
    total_sales: float
    sales_growth_pct: float
    pending_orders: int
    preparing_orders: int
    delivered_orders: int
    cancelled_orders: int
    low_stock_count: int
    platform_orders: dict[str, int]
    platform_sales: dict[str, float]
    platform_sales_pct: dict[str, int]


class SalesTrendPoint(BaseModel):
    date: str
    day: str
    total: float
    zomato: float
    swiggy: float
    website: float
    orders_count: int


class TopSellingItem(BaseModel):
    item_name: str
    portion_size: str
    quantity_sold: int
    total_revenue: float
    share_pct: float


class LowStockAlert(BaseModel):
    id: int
    name: str
    category: str
    current_stock: float
    minimum_stock: float
    reorder_level: float
    unit: str
    is_critical: bool


class RecentOrderSummary(BaseModel):
    id: int
    order_number: str
    platform: str
    customer_name: str
    customer_phone: str
    items_summary: str | None = None
    total_amount: float
    order_status: str
    payment_status: str
    created_at: datetime
    time_formatted: str


class DashboardResponse(BaseModel):
    kpis: KPIStats
    sales_trend: list[SalesTrendPoint]
    top_selling_items: list[TopSellingItem]
    low_stock_alerts: list[LowStockAlert]
    recent_orders: list[RecentOrderSummary]
