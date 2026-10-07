import csv
import io
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import case, func
from sqlalchemy.orm import Session

from app.models.customer import Customer
from app.models.menu import MenuItem, MenuItemPortion
from app.models.order import Order, OrderItem
from app.schemas.analytics import (
    CustomerSegmentMetric,
    CustomerSegmentsResponse,
    DishCostingResponse,
    DishMarginMetric,
    HourlyVelocityCell,
    OrderVelocityResponse,
    PlatformBreakdownMetric,
    PlatformBreakdownResponse,
    PLSummaryResponse,
    SalesTrendItem,
    SalesTrendResponse,
    TopItemMetric,
    TopItemsResponse,
)


class AnalyticsService:
    def __init__(self, db: Session):
        self.db = db

    def get_sales_trend(self, days: int = 7) -> SalesTrendResponse:
        now = datetime.now(UTC)
        start_date = now - timedelta(days=days - 1)
        start_date_naive = start_date.replace(hour=0, minute=0, second=0, microsecond=0, tzinfo=None)

        # Single query with GROUP BY instead of loading all orders into memory
        trend_data = (
            self.db.query(
                func.date(Order.created_at).label("day"),
                Order.platform,
                func.count(Order.id).label("order_count"),
                func.sum(Order.total_amount).label("revenue"),
            )
            .filter(Order.created_at >= start_date_naive)
            .group_by(func.date(Order.created_at), Order.platform)
            .all()
        )

        # Build day buckets
        day_buckets: dict[str, dict[str, Any]] = {}
        for d in range(days):
            day_dt = start_date + timedelta(days=d)
            day_str = day_dt.strftime("%Y-%m-%d")
            day_name = day_dt.strftime("%a")
            day_buckets[day_str] = {
                "date": day_str,
                "day": day_name,
                "total_revenue": 0.0,
                "website_revenue": 0.0,
                "zomato_revenue": 0.0,
                "swiggy_revenue": 0.0,
                "order_count": 0,
            }

        total_rev = 0.0
        total_orders = 0

        for day, platform, order_count, revenue in trend_data:
            day_str = str(day)
            if day_str in day_buckets:
                amt = float(revenue or 0)
                day_buckets[day_str]["total_revenue"] += amt
                day_buckets[day_str]["order_count"] += order_count
                total_rev += amt
                total_orders += order_count

                p = str(platform or "").upper()
                if "ZOMATO" in p:
                    day_buckets[day_str]["zomato_revenue"] += amt
                elif "SWIGGY" in p:
                    day_buckets[day_str]["swiggy_revenue"] += amt
                else:
                    day_buckets[day_str]["website_revenue"] += amt

        items: list[SalesTrendItem] = []
        for day_str in sorted(day_buckets.keys()):
            b = day_buckets[day_str]
            orders_cnt = b["order_count"]
            tot = round(b["total_revenue"], 2)
            avg = round(tot / orders_cnt, 2) if orders_cnt > 0 else 0.0
            items.append(
                SalesTrendItem(
                    date=b["date"],
                    day=b["day"],
                    total_revenue=tot,
                    website_revenue=round(b["website_revenue"], 2),
                    zomato_revenue=round(b["zomato_revenue"], 2),
                    swiggy_revenue=round(b["swiggy_revenue"], 2),
                    order_count=orders_cnt,
                    avg_order_value=avg,
                )
            )

        aov = round(total_rev / total_orders, 2) if total_orders > 0 else 0.0
        return SalesTrendResponse(
            items=items,
            total_period_revenue=round(total_rev, 2),
            total_period_orders=total_orders,
            average_order_value=aov,
        )

    def get_top_items(self, days: int = 30, limit: int = 10, sort_by: str = "revenue") -> TopItemsResponse:
        start_date = datetime.now(UTC) - timedelta(days=days)
        start_date_naive = start_date.replace(tzinfo=None)

        results = (
            self.db.query(
                OrderItem.item_name,
                func.sum(OrderItem.quantity).label("total_qty"),
                func.sum(OrderItem.total_price).label("total_rev"),
            )
            .join(Order, Order.id == OrderItem.order_id)
            .filter(Order.created_at >= start_date_naive)
            .group_by(OrderItem.item_name)
            .all()
        )

        all_rev = sum(float(r[2] or 0.0) for r in results)
        all_qty = sum(int(r[1] or 0) for r in results)

        items_list = []
        for idx, (name, qty, rev) in enumerate(results):
            qty = int(qty or 0)
            rev = float(rev or 0.0)
            pct = round((rev / all_rev * 100), 1) if all_rev > 0 else 0.0
            cat_name = "Biryani Special" if "biryani" in name.lower() else "Starters & Accompaniments"
            items_list.append(
                TopItemMetric(
                    item_id=idx + 1,
                    item_name=name,
                    category_name=cat_name,
                    quantity_sold=qty,
                    total_revenue=round(rev, 2),
                    percentage_of_total=pct,
                )
            )

        if sort_by == "quantity":
            items_list.sort(key=lambda x: x.quantity_sold, reverse=True)
        else:
            items_list.sort(key=lambda x: x.total_revenue, reverse=True)

        return TopItemsResponse(
            items=items_list[:limit],
            total_items_sold=all_qty,
            total_revenue=round(all_rev, 2),
        )

    def get_platform_breakdown(self, days: int = 30) -> PlatformBreakdownResponse:
        start_date = datetime.now(UTC) - timedelta(days=days)
        start_date_naive = start_date.replace(tzinfo=None)

        # Single query with GROUP BY instead of loading all orders
        platform_data = (
            self.db.query(
                Order.platform,
                func.count(Order.id).label("order_count"),
                func.sum(Order.total_amount).label("revenue"),
            )
            .filter(Order.created_at >= start_date_naive)
            .group_by(Order.platform)
            .all()
        )

        stats = {
            "WEBSITE": {"count": 0, "rev": 0.0, "name": "Direct Website", "rate": 0.0},
            "ZOMATO": {"count": 0, "rev": 0.0, "name": "Zomato Partner", "rate": 22.0},
            "SWIGGY": {"count": 0, "rev": 0.0, "name": "Swiggy Partner", "rate": 20.0},
        }

        total_gross = 0.0
        for platform, order_count, revenue in platform_data:
            p = str(platform or "").upper()
            amt = float(revenue or 0.0)
            total_gross += amt
            if "ZOMATO" in p:
                stats["ZOMATO"]["count"] = order_count
                stats["ZOMATO"]["rev"] = amt
            elif "SWIGGY" in p:
                stats["SWIGGY"]["count"] = order_count
                stats["SWIGGY"]["rev"] = amt
            else:
                stats["WEBSITE"]["count"] = order_count
                stats["WEBSITE"]["rev"] = amt

        platforms_list: list[PlatformBreakdownMetric] = []
        total_comm = 0.0
        total_net = 0.0

        for key in ["WEBSITE", "ZOMATO", "SWIGGY"]:
            item = stats[key]
            rev = item["rev"]
            cnt = item["count"]
            rate = item["rate"]
            comm = round(rev * (rate / 100.0), 2)
            net = round(rev - comm, 2)
            share = round((rev / total_gross * 100), 1) if total_gross > 0 else 0.0
            aov = round(rev / cnt, 2) if cnt > 0 else 0.0

            total_comm += comm
            total_net += net

            platforms_list.append(
                PlatformBreakdownMetric(
                    platform=key,
                    display_name=item["name"],
                    revenue=round(rev, 2),
                    order_count=cnt,
                    avg_order_value=aov,
                    revenue_share_pct=share,
                    commission_rate_pct=rate,
                    commission_amount=comm,
                    net_revenue=net,
                )
            )

        return PlatformBreakdownResponse(
            platforms=platforms_list,
            total_gross_revenue=round(total_gross, 2),
            total_commission=round(total_comm, 2),
            total_net_revenue=round(total_net, 2),
        )

    def get_order_velocity(self, days: int = 30) -> OrderVelocityResponse:
        start_date = datetime.now(UTC) - timedelta(days=days)
        start_date_naive = start_date.replace(tzinfo=None)

        # Single query with GROUP BY instead of loading all orders
        velocity_data = (
            self.db.query(
                func.extract("dow", Order.created_at).label("dow"),
                func.extract("hour", Order.created_at).label("hour"),
                func.count(Order.id).label("order_count"),
                func.sum(Order.total_amount).label("revenue"),
            )
            .filter(Order.created_at >= start_date_naive)
            .group_by(func.extract("dow", Order.created_at), func.extract("hour", Order.created_at))
            .all()
        )

        day_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        matrix = {(d, h): {"count": 0, "rev": 0.0} for d in range(7) for h in range(24)}

        peak_hour = 20
        peak_day = "Sun"
        max_orders = 0
        total_analyzed = 0

        for dow, hour, order_count, revenue in velocity_data:
            d = int(dow) % 7  # Convert to 0-6 (Monday=0)
            h = int(hour)
            matrix[(d, h)]["count"] = order_count
            matrix[(d, h)]["rev"] = float(revenue or 0.0)
            total_analyzed += order_count
            if order_count > max_orders:
                max_orders = order_count
                peak_hour = h
                peak_day = day_names[d]

        cells: list[HourlyVelocityCell] = []
        for dow in range(7):
            for h in range(24):
                slot = matrix[(dow, h)]
                cells.append(
                    HourlyVelocityCell(
                        day_of_week=dow,
                        day_name=day_names[dow],
                        hour=h,
                        order_count=slot["count"],
                        revenue=round(slot["rev"], 2),
                    )
                )

        return OrderVelocityResponse(
            cells=cells,
            peak_hour=peak_hour,
            peak_day=peak_day,
            max_orders_in_slot=max_orders,
            total_orders_analyzed=total_analyzed,
        )

    def get_customer_segments(self) -> CustomerSegmentsResponse:
        # Single query with GROUP BY instead of loading all customers
        segment_data = (
            self.db.query(
                Customer.segment,
                func.count(Customer.id).label("customer_count"),
                func.sum(Customer.total_spent).label("total_spent"),
            )
            .group_by(Customer.segment)
            .all()
        )

        total_cust = 0
        buckets = {
            "VIP": {"count": 0, "spent": 0.0},
            "REGULAR": {"count": 0, "spent": 0.0},
            "LAPSED": {"count": 0, "spent": 0.0},
            "NEW": {"count": 0, "spent": 0.0},
        }

        total_rev = 0.0
        for segment, customer_count, total_spent in segment_data:
            seg = str(segment or "NEW").upper()
            if seg not in buckets:
                seg = "NEW"
            spent = float(total_spent or 0.0)
            buckets[seg]["count"] = customer_count
            buckets[seg]["spent"] = spent
            total_cust += customer_count
            total_rev += spent

        metrics: list[CustomerSegmentMetric] = []
        for seg in ["VIP", "REGULAR", "LAPSED", "NEW"]:
            cnt = buckets[seg]["count"]
            spent = buckets[seg]["spent"]
            pct = round((cnt / total_cust * 100), 1) if total_cust > 0 else 0.0
            avg_spent = round(spent / cnt, 2) if cnt > 0 else 0.0
            metrics.append(
                CustomerSegmentMetric(
                    segment=seg,
                    customer_count=cnt,
                    percentage=pct,
                    total_spent=round(spent, 2),
                    avg_spent_per_customer=avg_spent,
                )
            )

        return CustomerSegmentsResponse(
            segments=metrics,
            total_customers=total_cust,
            total_revenue=round(total_rev, 2),
        )

    def get_dish_costing(self) -> DishCostingResponse:
        # Load all dishes with portions
        portions = self.db.query(MenuItemPortion).join(MenuItem, MenuItem.id == MenuItemPortion.menu_item_id).all()

        dishes_list: list[DishMarginMetric] = []
        low_count = 0
        total_margin_sum = 0.0

        for p in portions:
            dish = p.menu_item
            if not dish:
                continue

            selling_price = float(p.base_price or 350.0)
            # Food cost either from cost_price or calculated default ~32%
            food_cost = float(p.cost_price) if p.cost_price and p.cost_price > 0 else round(selling_price * 0.30, 2)
            # Packaging cost: 500g / 1kg containers + carry bag
            packaging_cost = 18.0 if "1kg" in (p.portion_size or "") else 14.0
            # Platform average commission ~12% (weighted direct vs Zomato/Swiggy)
            avg_comm = round(selling_price * 0.12, 2)

            net_margin = round(selling_price - food_cost - packaging_cost - avg_comm, 2)
            margin_pct = round((net_margin / selling_price * 100), 1) if selling_price > 0 else 0.0
            is_low = margin_pct < 50.0
            if is_low:
                low_count += 1
            total_margin_sum += margin_pct

            dishes_list.append(
                DishMarginMetric(
                    item_id=p.id,
                    item_name=f"{dish.name} ({p.portion_size})",
                    category_name="Biryani" if "biryani" in dish.name.lower() else "Accompaniment",
                    selling_price=selling_price,
                    food_cost=food_cost,
                    packaging_cost=packaging_cost,
                    avg_commission=avg_comm,
                    net_margin_amount=net_margin,
                    gross_margin_pct=margin_pct,
                    is_low_margin=is_low,
                )
            )

        avg_margin = round(total_margin_sum / len(dishes_list), 1) if dishes_list else 58.0
        return DishCostingResponse(
            dishes=dishes_list,
            avg_kitchen_margin_pct=avg_margin,
            low_margin_count=low_count,
        )

    def get_pl_summary(self, days: int = 30) -> PLSummaryResponse:
        start_date = datetime.now(UTC) - timedelta(days=days)
        start_date_naive = start_date.replace(tzinfo=None)

        # Single query with conditional aggregation instead of loading all orders
        result = (
            self.db.query(
                func.count(Order.id).label("order_count"),
                func.sum(Order.total_amount).label("gross_revenue"),
                func.sum(
                    case(
                        (Order.platform == "ZOMATO", Order.total_amount * 0.22),
                        (Order.platform == "SWIGGY", Order.total_amount * 0.20),
                        else_=0.0,
                    )
                ).label("commissions"),
            )
            .filter(Order.created_at >= start_date_naive)
            .first()
        )

        order_count = result.order_count or 0
        gross_rev = float(result.gross_revenue or 0.0)
        commissions = round(float(result.commissions or 0.0), 2)

        # Realistic Food Cost ratio ~30%, Packaging ~4.5%, Platform commissions ~13.5%
        ingredient_cost = round(gross_rev * 0.30, 2)
        packaging_cost = round(gross_rev * 0.045, 2)

        total_cogs = round(ingredient_cost + packaging_cost + commissions, 2)
        gross_profit = round(gross_rev - total_cogs, 2)
        margin_pct = round((gross_profit / gross_rev * 100), 1) if gross_rev > 0 else 0.0

        return PLSummaryResponse(
            gross_revenue=round(gross_rev, 2),
            ingredient_food_cost=ingredient_cost,
            packaging_cost=packaging_cost,
            platform_commissions=commissions,
            total_cogs=total_cogs,
            gross_profit=gross_profit,
            gross_profit_margin_pct=margin_pct,
            orders_count=order_count,
        )

    def export_csv(self, dataset: str, days: int = 30) -> str:
        output = io.StringIO()
        writer = csv.writer(output)

        if dataset == "sales":
            trend = self.get_sales_trend(days)
            writer.writerow(
                ["Date", "Day", "Total Revenue", "Website Revenue", "Zomato Revenue", "Swiggy Revenue", "Orders", "AOV"]
            )
            for item in trend.items:
                writer.writerow(
                    [
                        item.date,
                        item.day,
                        item.total_revenue,
                        item.website_revenue,
                        item.zomato_revenue,
                        item.swiggy_revenue,
                        item.order_count,
                        item.avg_order_value,
                    ]
                )

        elif dataset == "top_items":
            top = self.get_top_items(days=days, limit=50)
            writer.writerow(["Dish Name", "Category", "Quantity Sold", "Total Revenue", "Revenue Share %"])
            for item in top.items:
                writer.writerow(
                    [
                        item.item_name,
                        item.category_name,
                        item.quantity_sold,
                        item.total_revenue,
                        item.percentage_of_total,
                    ]
                )

        elif dataset == "costing":
            costing = self.get_dish_costing()
            writer.writerow(
                [
                    "Dish & Portion",
                    "Category",
                    "Selling Price",
                    "Food Cost",
                    "Packaging Cost",
                    "Avg Commission",
                    "Net Profit",
                    "Gross Margin %",
                    "Low Margin Alert",
                ]
            )
            for d in costing.dishes:
                writer.writerow(
                    [
                        d.item_name,
                        d.category_name,
                        d.selling_price,
                        d.food_cost,
                        d.packaging_cost,
                        d.avg_commission,
                        d.net_margin_amount,
                        d.gross_margin_pct,
                        "YES" if d.is_low_margin else "NO",
                    ]
                )

        else:  # platforms
            breakdown = self.get_platform_breakdown(days)
            writer.writerow(
                [
                    "Platform",
                    "Gross Revenue",
                    "Orders",
                    "Avg Order Value",
                    "Revenue Share %",
                    "Commission Rate %",
                    "Commission Deducted",
                    "Net Revenue",
                ]
            )
            for p in breakdown.platforms:
                writer.writerow(
                    [
                        p.display_name,
                        p.revenue,
                        p.order_count,
                        p.avg_order_value,
                        p.revenue_share_pct,
                        p.commission_rate_pct,
                        p.commission_amount,
                        p.net_revenue,
                    ]
                )

        return output.getvalue()
