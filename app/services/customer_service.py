from datetime import datetime, timezone, timedelta
from typing import List, Optional, Tuple
from app.core.exceptions import NotFoundException
from sqlalchemy import func, desc
from sqlalchemy.orm import Session

from app.models.customer import Customer, CustomerSegment
from app.models.order import Order, OrderItem
from app.schemas.customer import (
    CustomerDetailResponse,
    CustomerOrderBrief,
    CustomerResponse,
    CustomerSummary,
    CustomerUpdate,
)
from app.utils.pagination import calc_pages


def _compute_segment(customer: Customer) -> str:
    """Auto-compute customer segment based on recency & frequency."""
    now = datetime.now(timezone.utc)
    days_since_last = None
    if customer.last_order_date:
        last = customer.last_order_date
        if last.tzinfo is None:
            last = last.replace(tzinfo=timezone.utc)
        days_since_last = (now - last).days

    if customer.total_orders == 0:
        return CustomerSegment.NEW.value
    if customer.total_spent >= 5000 and customer.total_orders >= 10:
        return CustomerSegment.VIP.value
    if days_since_last is not None and days_since_last > 30:
        return CustomerSegment.LAPSED.value
    return CustomerSegment.REGULAR.value


class CustomerService:
    def __init__(self, db: Session):
        self.db = db

    def get_summary(self) -> CustomerSummary:
        now = datetime.now(timezone.utc)
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        total = self.db.query(func.count(Customer.id)).scalar() or 0
        total_revenue = self.db.query(func.coalesce(func.sum(Customer.total_spent), 0.0)).scalar() or 0.0
        avg_spent = self.db.query(func.coalesce(func.avg(Customer.total_spent), 0.0)).scalar() or 0.0

        # Segment counts
        vip = self.db.query(func.count(Customer.id)).filter(Customer.segment == CustomerSegment.VIP.value).scalar() or 0
        regular = self.db.query(func.count(Customer.id)).filter(Customer.segment == CustomerSegment.REGULAR.value).scalar() or 0
        lapsed = self.db.query(func.count(Customer.id)).filter(Customer.segment == CustomerSegment.LAPSED.value).scalar() or 0

        # New this month
        new_count = self.db.query(func.count(Customer.id)).filter(Customer.created_at >= month_start).scalar() or 0

        return CustomerSummary(
            total_customers=total,
            new_customers=new_count,
            vip_customers=vip,
            regular_customers=regular,
            lapsed_customers=lapsed,
            total_revenue=total_revenue,
            average_order_value=round(avg_spent, 2),
        )

    def list_customers(
        self,
        page: int = 1,
        page_size: int = 20,
        search: Optional[str] = None,
        segment: Optional[str] = None,
        sort_by: str = "total_spent",
    ) -> Tuple[List[CustomerResponse], int, int]:
        query = self.db.query(Customer)

        if search:
            like = f"%{search}%"
            query = query.filter(
                (Customer.name.ilike(like))
                | (Customer.phone.ilike(like))
                | (Customer.email.ilike(like))
            )

        if segment and segment != "ALL":
            query = query.filter(Customer.segment == segment)

        # Sort
        sort_col = {
            "total_spent": Customer.total_spent,
            "total_orders": Customer.total_orders,
            "last_order": Customer.last_order_date,
            "name": Customer.name,
            "newest": Customer.created_at,
        }.get(sort_by, Customer.total_spent)
        query = query.order_by(desc(sort_col))

        total = query.count()
        pages = calc_pages(total, page_size)
        items = query.offset((page - 1) * page_size).limit(page_size).all()

        # Refresh segments
        for c in items:
            computed = _compute_segment(c)
            if c.segment != computed:
                c.segment = computed
        self.db.flush()

        return [CustomerResponse.from_orm_with_avg(c) for c in items], total, pages

    def get_customer(self, customer_id: int) -> CustomerDetailResponse:
        customer = self.db.query(Customer).filter(Customer.id == customer_id).first()
        if not customer:
            raise NotFoundException("Customer")

        # Refresh segment
        customer.segment = _compute_segment(customer)
        self.db.flush()

        # Recent orders (last 20)
        recent_orders = (
            self.db.query(Order)
            .filter(Order.customer_id == customer_id)
            .order_by(desc(Order.created_at))
            .limit(20)
            .all()
        )

        order_briefs = [
            CustomerOrderBrief(
                id=o.id,
                order_number=o.order_number,
                platform=o.platform,
                order_status=o.order_status,
                total_amount=o.total_amount,
                items_summary=o.items_summary,
                items_count=getattr(o, "items_count", 1),
                created_at=o.created_at,
            )
            for o in recent_orders
        ]

        # Preferred platform
        platform_counts = (
            self.db.query(Order.platform, func.count(Order.id).label("cnt"))
            .filter(Order.customer_id == customer_id)
            .group_by(Order.platform)
            .order_by(desc("cnt"))
            .first()
        )
        preferred_platform = platform_counts[0] if platform_counts else None

        # Preferred item (most ordered)
        top_item = (
            self.db.query(OrderItem.item_name, func.sum(OrderItem.quantity).label("qty"))
            .join(Order, Order.id == OrderItem.order_id)
            .filter(Order.customer_id == customer_id)
            .group_by(OrderItem.item_name)
            .order_by(desc("qty"))
            .first()
        )
        preferred_item = top_item[0] if top_item else None

        base = CustomerResponse.from_orm_with_avg(customer)
        return CustomerDetailResponse(
            **base.model_dump(),
            recent_orders=order_briefs,
            preferred_platform=preferred_platform,
            preferred_item=preferred_item,
        )

    def update_customer(self, customer_id: int, payload: CustomerUpdate) -> CustomerResponse:
        customer = self.db.query(Customer).filter(Customer.id == customer_id).first()
        if not customer:
            raise NotFoundException("Customer")

        if payload.name is not None:
            customer.name = payload.name
        if payload.email is not None:
            customer.email = payload.email
        if payload.default_address is not None:
            customer.default_address = payload.default_address
        if payload.notes is not None:
            customer.notes = payload.notes

        customer.segment = _compute_segment(customer)
        self.db.commit()
        self.db.refresh(customer)
        return CustomerResponse.from_orm_with_avg(customer)

    def add_note(self, customer_id: int, note: str) -> CustomerResponse:
        customer = self.db.query(Customer).filter(Customer.id == customer_id).first()
        if not customer:
            raise NotFoundException("Customer")

        existing = customer.notes or ""
        timestamp = datetime.now(timezone.utc).strftime("%d %b %Y %H:%M")
        customer.notes = f"[{timestamp}] {note}\n{existing}".strip()
        self.db.commit()
        self.db.refresh(customer)
        return CustomerResponse.from_orm_with_avg(customer)

    def get_customer_orders(
        self,
        customer_id: int,
        page: int = 1,
        page_size: int = 10,
    ) -> Tuple[List[CustomerOrderBrief], int, int]:
        customer = self.db.query(Customer).filter(Customer.id == customer_id).first()
        if not customer:
            raise NotFoundException("Customer")

        query = (
            self.db.query(Order)
            .filter(Order.customer_id == customer_id)
            .order_by(desc(Order.created_at))
        )
        total = query.count()
        pages = calc_pages(total, page_size)
        orders = query.offset((page - 1) * page_size).limit(page_size).all()

        return (
            [
                CustomerOrderBrief(
                    id=o.id,
                    order_number=o.order_number,
                    platform=o.platform,
                    order_status=o.order_status,
                    total_amount=o.total_amount,
                    items_summary=o.items_summary,
                    items_count=getattr(o, "items_count", 1),
                    created_at=o.created_at,
                )
                for o in orders
            ],
            total,
            pages,
        )

    def refresh_all_segments(self) -> int:
        """Batch-refresh segments for all customers. Returns count updated."""
        customers = self.db.query(Customer).all()
        updated = 0
        for c in customers:
            new_seg = _compute_segment(c)
            if c.segment != new_seg:
                c.segment = new_seg
                updated += 1
        self.db.commit()
        return updated
