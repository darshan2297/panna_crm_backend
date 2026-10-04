from datetime import UTC, datetime
from typing import Any

from sqlalchemy import desc, func, or_
from sqlalchemy.orm import Session, joinedload

from app.models.customer import Customer
from app.models.order import Order, OrderItem, OrderPlatform, OrderStatus
from app.models.order_history import OrderStatusHistory
from app.repositories.base import BaseRepository


class OrderRepository(BaseRepository[Order]):
    def __init__(self, db: Session):
        super().__init__(Order, db)

    def get_by_id_with_relations(self, order_id: int) -> Order | None:
        """Fetch order by ID with eagerly loaded items, status_history, and customer."""
        return (
            self.db.query(Order)
            .options(
                joinedload(Order.items),
                joinedload(Order.status_history),
                joinedload(Order.customer),
            )
            .filter(Order.id == order_id)
            .first()
        )

    def get_by_order_number(self, order_number: str) -> Order | None:
        return (
            self.db.query(Order)
            .options(
                joinedload(Order.items),
                joinedload(Order.status_history),
                joinedload(Order.customer),
            )
            .filter(Order.order_number == order_number)
            .first()
        )

    def get_filtered_orders(
        self,
        skip: int = 0,
        limit: int = 20,
        platform: str | None = None,
        status: str | None = None,
        payment_status: str | None = None,
        search: str | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
    ) -> tuple[list[Order], int]:
        """Query orders with flexible search, filter, and pagination."""
        query = self.db.query(Order)

        if platform and platform.upper() != "ALL":
            query = query.filter(Order.platform == platform.upper())

        if status and status.upper() != "ALL":
            query = query.filter(Order.order_status == status.upper())

        if payment_status and payment_status.upper() != "ALL":
            query = query.filter(Order.payment_status == payment_status.upper())

        if search:
            search_pat = f"%{search.strip()}%"
            query = query.filter(
                or_(
                    Order.order_number.ilike(search_pat),
                    Order.customer_name.ilike(search_pat),
                    Order.customer_phone.ilike(search_pat),
                    Order.items_summary.ilike(search_pat),
                )
            )

        if date_from and date_from.tzinfo:
            date_from = date_from.astimezone(UTC).replace(tzinfo=None)
        if date_to and date_to.tzinfo:
            date_to = date_to.astimezone(UTC).replace(tzinfo=None)

        if date_from:
            query = query.filter(Order.created_at >= date_from)

        if date_to:
            query = query.filter(Order.created_at <= date_to)

        total = query.count()
        orders = query.options(joinedload(Order.items)).order_by(desc(Order.created_at)).offset(skip).limit(limit).all()
        return orders, total

    def get_status_counts(
        self,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        platform: str | None = None,
    ) -> dict[str, Any]:
        """Get aggregate counts by order status and period metrics filtered by date range and platform."""
        if date_from and date_from.tzinfo:
            date_from = date_from.astimezone(UTC).replace(tzinfo=None)
        if date_to and date_to.tzinfo:
            date_to = date_to.astimezone(UTC).replace(tzinfo=None)

        base_query = self.db.query(Order)
        if platform and platform.upper() != "ALL":
            base_query = base_query.filter(Order.platform == platform.upper())

        filtered_query = base_query
        if date_from:
            filtered_query = filtered_query.filter(Order.created_at >= date_from)
        if date_to:
            filtered_query = filtered_query.filter(Order.created_at <= date_to)

        total_orders = filtered_query.with_entities(func.count(Order.id)).scalar() or 0

        status_rows = (
            filtered_query.with_entities(Order.order_status, func.count(Order.id)).group_by(Order.order_status).all()
        )
        status_map = {row[0]: row[1] for row in status_rows}

        revenue_query = filtered_query.with_entities(
            func.count(Order.id),
            func.coalesce(func.sum(Order.total_amount), 0.0),
        ).first()

        period_orders = revenue_query[0] if revenue_query else 0
        period_revenue = float(revenue_query[1]) if revenue_query else 0.0

        return {
            "total_orders": total_orders,
            "new": status_map.get(OrderStatus.NEW.value, 0),
            "confirmed": status_map.get(OrderStatus.CONFIRMED.value, 0),
            "preparing": status_map.get(OrderStatus.PREPARING.value, 0),
            "ready": status_map.get(OrderStatus.READY.value, 0),
            "out_for_delivery": status_map.get(OrderStatus.OUT_FOR_DELIVERY.value, 0),
            "delivered": status_map.get(OrderStatus.DELIVERED.value, 0),
            "cancelled": status_map.get(OrderStatus.CANCELLED.value, 0),
            "today_orders": period_orders,
            "today_revenue": round(period_revenue, 2),
        }

    def generate_next_order_number(self, platform: str) -> str:
        """Generate human-readable unique order number."""
        now = datetime.now(UTC)
        date_str = now.strftime("%Y%m%d")
        prefix = "PB"
        if platform == OrderPlatform.ZOMATO.value:
            prefix = "PB-Z"
        elif platform == OrderPlatform.SWIGGY.value:
            prefix = "PB-S"
        else:
            prefix = "PB-W"

        # Count orders for this prefix to avoid collisions
        count = self.db.query(func.count(Order.id)).scalar() or 0
        new_seq = count + 1001
        return f"{prefix}-{date_str}-{new_seq}"

    def get_or_create_customer(
        self,
        name: str,
        phone: str,
        email: str | None = None,
        address: str | None = None,
        order_amount: float = 0.0,
    ) -> Customer:
        """Find customer by phone or create new record, updating their stats."""
        clean_phone = phone.strip()
        customer = self.db.query(Customer).filter(Customer.phone == clean_phone).first()

        if customer:
            if name and not customer.name:
                customer.name = name
            if email and not customer.email:
                customer.email = email
            if address and not customer.default_address:
                customer.default_address = address
            customer.total_orders += 1
            customer.total_spent += order_amount
        else:
            customer = Customer(
                name=name,
                phone=clean_phone,
                email=email,
                default_address=address,
                total_orders=1,
                total_spent=order_amount,
            )
            self.db.add(customer)

        self.db.flush()
        return customer

    def create_order_with_items_and_history(
        self,
        order: Order,
        items: list[OrderItem],
        changed_by_name: str = "System",
        initial_notes: str = "Order received and created",
    ) -> Order:
        """Create order, link items, and record initial OrderStatusHistory entry."""
        self.db.add(order)
        self.db.flush()

        for item in items:
            item.order_id = order.id
            self.db.add(item)

        history_entry = OrderStatusHistory(
            order_id=order.id,
            previous_status=None,
            new_status=order.order_status,
            changed_by_name=changed_by_name,
            notes=initial_notes,
        )
        self.db.add(history_entry)
        self.db.commit()
        self.db.refresh(order)
        return order

    def add_status_history(
        self,
        order_id: int,
        previous_status: str | None,
        new_status: str,
        changed_by_name: str,
        notes: str | None = None,
    ) -> OrderStatusHistory:
        """Append a state transition log entry."""
        history = OrderStatusHistory(
            order_id=order_id,
            previous_status=previous_status,
            new_status=new_status,
            changed_by_name=changed_by_name,
            notes=notes,
        )
        self.db.add(history)
        self.db.commit()
        self.db.refresh(history)
        return history
