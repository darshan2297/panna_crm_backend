from datetime import UTC, datetime, timedelta

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.inventory import InventoryItem
from app.models.order import Order, OrderItem, OrderPlatform, OrderStatus
from app.schemas.dashboard import (
    DashboardResponse,
    KPIStats,
    LowStockAlert,
    RecentOrderSummary,
    SalesTrendPoint,
    TopSellingItem,
)


class DashboardService:
    def __init__(self, db: Session):
        self.db = db

    def get_dashboard_data(self) -> DashboardResponse:
        now = datetime.now(UTC)
        today_start = datetime(now.year, now.month, now.day, tzinfo=UTC)
        yesterday_start = today_start - timedelta(days=1)

        # 1. Orders today vs yesterday
        today_orders = self.db.query(Order).filter(Order.created_at >= today_start).all()
        yesterday_orders = self.db.query(Order).filter(
            Order.created_at >= yesterday_start, Order.created_at < today_start
        ).all()

        today_orders_count = len(today_orders) if today_orders else 1
        yesterday_orders_count = len(yesterday_orders) if yesterday_orders else 1

        today_sales = sum(o.total_amount for o in today_orders if o.order_status != OrderStatus.CANCELLED.value)
        yesterday_sales = sum(o.total_amount for o in yesterday_orders if o.order_status != OrderStatus.CANCELLED.value)

        # Growth calculation
        orders_growth = round(((today_orders_count - yesterday_orders_count) / yesterday_orders_count) * 100, 1)
        sales_growth = round(((today_sales - yesterday_sales) / max(yesterday_sales, 1.0)) * 100, 1)

        # Status breakdowns
        pending_orders = len([o for o in today_orders if o.order_status in [OrderStatus.NEW.value, OrderStatus.CONFIRMED.value]])
        preparing_orders = len([o for o in today_orders if o.order_status == OrderStatus.PREPARING.value])
        delivered_orders = len([o for o in today_orders if o.order_status == OrderStatus.DELIVERED.value])
        cancelled_orders = len([o for o in today_orders if o.order_status == OrderStatus.CANCELLED.value])

        # Platform breakdowns
        platform_orders = {
            OrderPlatform.ZOMATO.value: len([o for o in today_orders if o.platform == OrderPlatform.ZOMATO.value]),
            OrderPlatform.SWIGGY.value: len([o for o in today_orders if o.platform == OrderPlatform.SWIGGY.value]),
            OrderPlatform.WEBSITE.value: len([o for o in today_orders if o.platform == OrderPlatform.WEBSITE.value]),
        }

        platform_sales = {
            OrderPlatform.ZOMATO.value: sum(o.total_amount for o in today_orders if o.platform == OrderPlatform.ZOMATO.value and o.order_status != OrderStatus.CANCELLED.value),
            OrderPlatform.SWIGGY.value: sum(o.total_amount for o in today_orders if o.platform == OrderPlatform.SWIGGY.value and o.order_status != OrderStatus.CANCELLED.value),
            OrderPlatform.WEBSITE.value: sum(o.total_amount for o in today_orders if o.platform == OrderPlatform.WEBSITE.value and o.order_status != OrderStatus.CANCELLED.value),
        }

        total_valid_sales = max(sum(platform_sales.values()), 1.0)
        platform_sales_pct = {
            plat: round((amt / total_valid_sales) * 100)
            for plat, amt in platform_sales.items()
        }

        # 2. Low Stock Alerts
        inventory_items = self.db.query(InventoryItem).filter(InventoryItem.is_active == True).all()
        low_stock_list: list[LowStockAlert] = []
        for inv in inventory_items:
            if inv.current_stock <= inv.reorder_level:
                low_stock_list.append(
                    LowStockAlert(
                        id=inv.id,
                        name=inv.name,
                        category=inv.category,
                        current_stock=inv.current_stock,
                        minimum_stock=inv.minimum_stock,
                        reorder_level=inv.reorder_level,
                        unit=inv.unit,
                        is_critical=inv.current_stock <= inv.minimum_stock,
                    )
                )

        # 3. 7-Day Sales Trend
        sales_trend: list[SalesTrendPoint] = []
        for days_back in range(6, -1, -1):
            day_dt = now - timedelta(days=days_back)
            d_start = datetime(day_dt.year, day_dt.month, day_dt.day, tzinfo=UTC)
            d_end = d_start + timedelta(days=1)

            day_orders = self.db.query(Order).filter(
                Order.created_at >= d_start,
                Order.created_at < d_end,
                Order.order_status != OrderStatus.CANCELLED.value,
            ).all()

            z_sales = sum(o.total_amount for o in day_orders if o.platform == OrderPlatform.ZOMATO.value)
            s_sales = sum(o.total_amount for o in day_orders if o.platform == OrderPlatform.SWIGGY.value)
            w_sales = sum(o.total_amount for o in day_orders if o.platform == OrderPlatform.WEBSITE.value)
            tot = z_sales + s_sales + w_sales

            sales_trend.append(
                SalesTrendPoint(
                    date=d_start.strftime("%Y-%m-%d"),
                    day=d_start.strftime("%a"),
                    total=tot,
                    zomato=z_sales,
                    swiggy=s_sales,
                    website=w_sales,
                    orders_count=len(day_orders),
                )
            )

        # 4. Top Selling Items
        top_items_raw = (
            self.db.query(
                OrderItem.item_name,
                OrderItem.portion_size,
                func.sum(OrderItem.quantity).label("total_qty"),
                func.sum(OrderItem.total_price).label("revenue"),
            )
            .group_by(OrderItem.item_name, OrderItem.portion_size)
            .order_by(func.sum(OrderItem.quantity).desc())
            .limit(5)
            .all()
        )

        overall_rev = sum(item[3] for item in top_items_raw) if top_items_raw else 1.0
        top_selling_items = [
            TopSellingItem(
                item_name=item[0],
                portion_size=item[1],
                quantity_sold=int(item[2]),
                total_revenue=float(item[3]),
                share_pct=round((float(item[3]) / max(overall_rev, 1.0)) * 100, 1),
            )
            for item in top_items_raw
        ]

        # 5. Recent Orders
        recent_orders_raw = (
            self.db.query(Order)
            .order_by(Order.created_at.desc())
            .limit(10)
            .all()
        )

        recent_orders = [
            RecentOrderSummary(
                id=o.id,
                order_number=o.order_number,
                platform=o.platform,
                customer_name=o.customer_name,
                customer_phone=o.customer_phone,
                items_summary=o.items_summary or "Biryani Items",
                total_amount=o.total_amount,
                order_status=o.order_status,
                payment_status=o.payment_status,
                created_at=o.created_at,
                time_formatted=o.created_at.strftime("%I:%M %p"),
            )
            for o in recent_orders_raw
        ]

        return DashboardResponse(
            kpis=KPIStats(
                total_orders=today_orders_count,
                orders_growth_pct=orders_growth,
                total_sales=today_sales,
                sales_growth_pct=sales_growth,
                pending_orders=pending_orders,
                preparing_orders=preparing_orders,
                delivered_orders=delivered_orders,
                cancelled_orders=cancelled_orders,
                low_stock_count=len(low_stock_list),
                platform_orders=platform_orders,
                platform_sales=platform_sales,
                platform_sales_pct=platform_sales_pct,
            ),
            sales_trend=sales_trend,
            top_selling_items=top_selling_items,
            low_stock_alerts=low_stock_list,
            recent_orders=recent_orders,
        )
