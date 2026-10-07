from datetime import UTC, datetime, timedelta
from typing import Any

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

        # 1. Orders today vs yesterday - use SQL aggregation instead of loading all rows
        today_stats = (
            self.db.query(
                func.count(Order.id).label("count"),
                func.sum(Order.total_amount).label("total"),
            )
            .filter(Order.created_at >= today_start)
            .first()
        )
        yesterday_stats = (
            self.db.query(
                func.count(Order.id).label("count"),
                func.sum(Order.total_amount).label("total"),
            )
            .filter(Order.created_at >= yesterday_start, Order.created_at < today_start)
            .first()
        )

        today_orders_count = today_stats.count or 0
        yesterday_orders_count = yesterday_stats.count or 0
        today_sales = float(today_stats.total or 0)
        yesterday_sales = float(yesterday_stats.total or 0)

        # Growth calculation
        orders_growth = round(((today_orders_count - yesterday_orders_count) / max(yesterday_orders_count, 1)) * 100, 1)
        sales_growth = round(((today_sales - yesterday_sales) / max(yesterday_sales, 1.0)) * 100, 1)

        # Status breakdowns - single query with GROUP BY
        status_counts = (
            self.db.query(Order.order_status, func.count(Order.id))
            .filter(Order.created_at >= today_start)
            .group_by(Order.order_status)
            .all()
        )
        status_map = {s: c for s, c in status_counts}
        pending_orders = status_map.get(OrderStatus.NEW.value, 0) + status_map.get(OrderStatus.CONFIRMED.value, 0)
        preparing_orders = status_map.get(OrderStatus.PREPARING.value, 0)
        delivered_orders = status_map.get(OrderStatus.DELIVERED.value, 0)
        cancelled_orders = status_map.get(OrderStatus.CANCELLED.value, 0)

        # Platform breakdowns - single query with GROUP BY
        platform_stats = (
            self.db.query(Order.platform, func.count(Order.id), func.sum(Order.total_amount))
            .filter(Order.created_at >= today_start)
            .group_by(Order.platform)
            .all()
        )
        platform_orders = {}
        platform_sales = {}
        for plat, cnt, rev in platform_stats:
            platform_orders[plat] = cnt
            platform_sales[plat] = float(rev or 0)

        # Ensure all platforms are present
        for p in [OrderPlatform.ZOMATO.value, OrderPlatform.SWIGGY.value, OrderPlatform.WEBSITE.value]:
            platform_orders.setdefault(p, 0)
            platform_sales.setdefault(p, 0.0)

        total_valid_sales = max(sum(platform_sales.values()), 1.0)
        platform_sales_pct = {plat: round((amt / total_valid_sales) * 100) for plat, amt in platform_sales.items()}

        # 2. Low Stock Alerts - single query for low stock items
        low_stock_items = (
            self.db.query(InventoryItem)
            .filter(InventoryItem.is_active == True, InventoryItem.current_stock <= InventoryItem.reorder_level)
            .all()
        )
        low_stock_list: list[LowStockAlert] = [
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
            for inv in low_stock_items
        ]

        # 3. 7-Day Sales Trend - single query with GROUP BY instead of 7 separate queries
        week_start = today_start - timedelta(days=6)
        trend_data = (
            self.db.query(
                func.date(Order.created_at).label("day"),
                Order.platform,
                func.count(Order.id).label("order_count"),
                func.sum(Order.total_amount).label("revenue"),
            )
            .filter(
                Order.created_at >= week_start,
                Order.order_status != OrderStatus.CANCELLED.value,
            )
            .group_by(func.date(Order.created_at), Order.platform)
            .all()
        )

        # Build trend buckets
        day_buckets: dict[str, dict[str, Any]] = {}
        for days_back in range(6, -1, -1):
            day_dt = now - timedelta(days=days_back)
            day_str = day_dt.strftime("%Y-%m-%d")
            day_buckets[day_str] = {
                "date": day_str,
                "day": day_dt.strftime("%a"),
                "total": 0.0,
                "zomato": 0.0,
                "swiggy": 0.0,
                "website": 0.0,
                "orders_count": 0,
            }

        for day, platform, order_count, revenue in trend_data:
            day_str = str(day)
            if day_str in day_buckets:
                amt = float(revenue or 0)
                day_buckets[day_str]["total"] += amt
                day_buckets[day_str]["orders_count"] += order_count
                p = str(platform or "").upper()
                if "ZOMATO" in p:
                    day_buckets[day_str]["zomato"] += amt
                elif "SWIGGY" in p:
                    day_buckets[day_str]["swiggy"] += amt
                else:
                    day_buckets[day_str]["website"] += amt

        sales_trend: list[SalesTrendPoint] = []
        for day_str in sorted(day_buckets.keys()):
            b = day_buckets[day_str]
            sales_trend.append(
                SalesTrendPoint(
                    date=b["date"],
                    day=b["day"],
                    total=round(b["total"], 2),
                    zomato=round(b["zomato"], 2),
                    swiggy=round(b["swiggy"], 2),
                    website=round(b["website"], 2),
                    orders_count=b["orders_count"],
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
        recent_orders_raw = self.db.query(Order).order_by(Order.created_at.desc()).limit(10).all()

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
