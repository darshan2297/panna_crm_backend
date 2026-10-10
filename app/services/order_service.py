from datetime import UTC, datetime

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.logging import logger
from app.models.order import Order, OrderItem, OrderPlatform, OrderStatus, PaymentStatus
from app.models.user import User
from app.repositories.order_repository import OrderRepository
from app.schemas.order import (
    CustomerBriefResponse,
    OrderCreate,
    OrderDetailResponse,
    OrderItemResponse,
    OrderResponse,
    OrderStatusHistoryResponse,
    OrderStatusSummary,
)
from app.schemas.public_order import (
    PaymentWebhookRequest,
    PaymentWebhookResponse,
    PublicOrderTrackResponse,
    TrackingTimelineStep,
    WebsiteOrderCreateRequest,
    WebsiteOrderCreateResponse,
)
from app.services.payment_service import payment_service
from app.services.platform_adapter import get_platform_adapter
from app.socket_manager import emit_event
from app.utils.pagination import calc_pages

# Allowed forward status transitions
VALID_TRANSITIONS: dict[str, list[str]] = {
    OrderStatus.NEW.value: [OrderStatus.CONFIRMED.value, OrderStatus.CANCELLED.value],
    OrderStatus.CONFIRMED.value: [OrderStatus.PREPARING.value, OrderStatus.CANCELLED.value],
    OrderStatus.PREPARING.value: [OrderStatus.READY.value, OrderStatus.CANCELLED.value],
    OrderStatus.READY.value: [
        OrderStatus.OUT_FOR_DELIVERY.value,
        OrderStatus.DELIVERED.value,
        OrderStatus.CANCELLED.value,
    ],
    OrderStatus.OUT_FOR_DELIVERY.value: [OrderStatus.DELIVERED.value, OrderStatus.CANCELLED.value],
    OrderStatus.DELIVERED.value: [],  # Terminal
    OrderStatus.CANCELLED.value: [],  # Terminal
}


class OrderService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = OrderRepository(db)

    def list_orders(
        self,
        page: int = 1,
        page_size: int = 20,
        platform: str | None = None,
        status: str | None = None,
        payment_status: str | None = None,
        search: str | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
    ) -> tuple[list[OrderResponse], int, int]:
        """Fetch paginated, filtered orders with summary formatting."""
        skip = (page - 1) * page_size
        orders, total = self.repo.get_filtered_orders(
            skip=skip,
            limit=page_size,
            platform=platform,
            status=status,
            payment_status=payment_status,
            search=search,
            date_from=date_from,
            date_to=date_to,
        )

        total_pages = calc_pages(total, page_size)

        order_responses = [
            OrderResponse(
                id=o.id,
                order_number=o.order_number,
                platform=o.platform,
                customer_id=o.customer_id,
                customer_name=o.customer_name,
                customer_phone=o.customer_phone,
                delivery_address=o.delivery_address,
                subtotal=o.subtotal,
                discount=o.discount,
                delivery_fee=o.delivery_fee,
                tax=o.tax,
                total_amount=o.total_amount,
                order_status=o.order_status,
                payment_status=o.payment_status,
                items_summary=o.items_summary,
                notes=o.notes,
                created_at=o.created_at,
                updated_at=o.updated_at,
                items_count=len(o.items) if o.items else 1,
            )
            for o in orders
        ]

        return order_responses, total, total_pages

    def get_order_details(self, order_id: int) -> OrderDetailResponse:
        """Fetch complete order details with items, history, customer, and platform metrics."""
        order = self.repo.get_by_id_with_relations(order_id)
        if not order:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Order with ID {order_id} not found",
            )

        adapter = get_platform_adapter(order.platform)
        commission = adapter.calculate_commission(order.total_amount)

        customer_brief = None
        if order.customer:
            customer_brief = CustomerBriefResponse(
                id=order.customer.id,
                name=order.customer.name,
                phone=order.customer.phone,
                email=order.customer.email,
                default_address=order.customer.default_address,
                total_orders=order.customer.total_orders,
                total_spent=order.customer.total_spent,
            )

        items_resp = [
            OrderItemResponse(
                id=item.id,
                order_id=item.order_id,
                item_name=item.item_name,
                portion_size=item.portion_size,
                quantity=item.quantity,
                unit_price=item.unit_price,
                total_price=item.total_price,
                cost_price=item.cost_price,
                is_free=item.is_free,
                created_at=item.created_at,
            )
            for item in order.items
        ]

        # Aggregate food cost for margin (free items cost the kitchen nothing).
        food_cost = round(
            sum(
                float(item.cost_price or 0.0) * item.quantity
                for item in order.items
                if not item.is_free
            ),
            2,
        )

        history_resp = [
            OrderStatusHistoryResponse(
                id=h.id,
                order_id=h.order_id,
                previous_status=h.previous_status,
                new_status=h.new_status,
                changed_by_name=h.changed_by_name,
                notes=h.notes,
                created_at=h.created_at,
            )
            for h in order.status_history
        ]

        return OrderDetailResponse(
            id=order.id,
            order_number=order.order_number,
            platform=order.platform,
            customer_id=order.customer_id,
            customer_name=order.customer_name,
            customer_phone=order.customer_phone,
            delivery_address=order.delivery_address,
            subtotal=order.subtotal,
            discount=order.discount,
            delivery_fee=order.delivery_fee,
            transaction_fee=order.transaction_fee,
            vas_fee=order.vas_fee,
            other_expense=order.other_expense,
            tax=order.tax,
            total_amount=order.total_amount,
            order_status=order.order_status,
            payment_status=order.payment_status,
            gateway=order.gateway,
            gateway_payment_id=order.gateway_payment_id,
            gateway_order_id=order.gateway_order_id,
            refund_id=order.refund_id,
            refund_amount=order.refund_amount,
            refunded_at=order.refunded_at,
            items_summary=order.items_summary,
            notes=order.notes,
            created_at=order.created_at,
            updated_at=order.updated_at,
            items_count=len(order.items),
            items=items_resp,
            status_history=history_resp,
            customer=customer_brief,
            platform_display=adapter.display_name,
            estimated_commission=commission,
            food_cost=food_cost,
        )

    def create_order(
        self,
        payload: OrderCreate,
        current_user: User | None = None,
    ) -> OrderDetailResponse:
        """Create new order with platform normalization, customer attribution, and status tracking."""
        adapter = get_platform_adapter(payload.platform)

        # Validate order payload
        is_valid, error_msg = adapter.validate_order(payload.model_dump())
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_msg or "Invalid order payload",
            )

        # Calculate item totals and compose items summary
        db_items: list[OrderItem] = []
        subtotal = 0.0
        summary_parts: list[str] = []

        for item_data in payload.items:
            item_total = round(item_data.unit_price * item_data.quantity, 2)
            subtotal += item_total
            summary_parts.append(f"{item_data.quantity}x {item_data.item_name} ({item_data.portion_size})")

            db_items.append(
                OrderItem(
                    item_name=item_data.item_name,
                    portion_size=item_data.portion_size,
                    quantity=item_data.quantity,
                    unit_price=item_data.unit_price,
                    total_price=item_total,
                )
            )

        subtotal = round(subtotal, 2)
        # Standard food tax GST 5% on taxable amount
        taxable_amount = max(0.0, subtotal - payload.discount)
        tax = round(taxable_amount * 0.05, 2)
        total_amount = round(taxable_amount + payload.delivery_fee + tax, 2)

        # Customer attribution
        customer = self.repo.get_or_create_customer(
            name=payload.customer_name,
            phone=payload.customer_phone,
            email=payload.customer_email,
            address=payload.delivery_address,
            order_amount=total_amount,
        )

        order_number = self.repo.generate_next_order_number(payload.platform.value)
        changed_by = current_user.full_name if current_user else "CRM Staff"

        order = Order(
            order_number=order_number,
            platform=payload.platform.value,
            customer_id=customer.id,
            customer_name=payload.customer_name,
            customer_phone=payload.customer_phone,
            delivery_address=payload.delivery_address or customer.default_address,
            subtotal=subtotal,
            discount=payload.discount,
            delivery_fee=payload.delivery_fee,
            tax=tax,
            total_amount=total_amount,
            order_status=OrderStatus.NEW.value,
            payment_status=payload.payment_status.value,
            items_summary=", ".join(summary_parts)[:490],
            notes=payload.notes,
        )

        created_order = self.repo.create_order_with_items_and_history(
            order=order,
            items=db_items,
            changed_by_name=changed_by,
            initial_notes=f"Order placed via {adapter.display_name}",
        )

        emit_event(
            "new_order",
            {
                "id": created_order.id,
                "order_number": created_order.order_number,
                "platform": created_order.platform,
                "customer_name": created_order.customer_name,
                "total_amount": created_order.total_amount,
                "items_summary": created_order.items_summary,
                "order_status": created_order.order_status,
            },
        )

        return self.get_order_details(created_order.id)

    def update_order_status(
        self,
        order_id: int,
        new_status: OrderStatus,
        notes: str | None = None,
        current_user: User | None = None,
    ) -> OrderDetailResponse:
        """Enforce state transitions and record status history log."""
        order = self.repo.get_by_id_with_relations(order_id)
        if not order:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Order with ID {order_id} not found",
            )

        current_st = order.order_status
        target_st = new_status.value

        # Check if order is already in target status
        if current_st == target_st:
            return self.get_order_details(order.id)

        # Terminal state check
        if current_st in [OrderStatus.DELIVERED.value, OrderStatus.CANCELLED.value]:
            # Only allow if explicitly authorized or raise error
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot change status of a completed order (current: {current_st})",
            )

        # Transition validation
        allowed_next = VALID_TRANSITIONS.get(current_st, [])
        if target_st not in allowed_next and current_user and current_user.role != "ADMIN":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid transition from {current_st} to {target_st}. Permitted: {', '.join(allowed_next)}",
            )

        # Apply update
        previous_status = order.order_status
        order.order_status = target_st
        self.db.commit()

        changed_by = current_user.full_name if current_user else "System"
        default_note = f"Status updated from {previous_status} to {target_st}"

        self.repo.add_status_history(
            order_id=order.id,
            previous_status=previous_status,
            new_status=target_st,
            changed_by_name=changed_by,
            notes=notes or default_note,
        )

        logger.info(f"Order #{order.order_number} transitioned: {previous_status} -> {target_st} by {changed_by}")
        emit_event(
            "order_status_changed",
            {
                "id": order.id,
                "order_number": order.order_number,
                "order_status": target_st,
                "previous_status": previous_status,
            },
        )
        return self.get_order_details(order.id)

    def cancel_order(
        self,
        order_id: int,
        reason: str,
        current_user: User | None = None,
    ) -> OrderDetailResponse:
        """Cancel an order with a mandatory reason note."""
        order = self.repo.get_by_id_with_relations(order_id)
        if not order:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Order with ID {order_id} not found",
            )

        if order.order_status == OrderStatus.DELIVERED.value:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot cancel an order that has already been delivered",
            )

        if order.order_status == OrderStatus.CANCELLED.value:
            return self.get_order_details(order.id)

        previous_status = order.order_status
        order.order_status = OrderStatus.CANCELLED.value
        self.db.commit()

        changed_by = current_user.full_name if current_user else "Staff"
        self.repo.add_status_history(
            order_id=order.id,
            previous_status=previous_status,
            new_status=OrderStatus.CANCELLED.value,
            changed_by_name=changed_by,
            notes=f"Order Cancelled: {reason}",
        )

        emit_event(
            "order_status_changed",
            {
                "id": order.id,
                "order_number": order.order_number,
                "order_status": OrderStatus.CANCELLED.value,
                "previous_status": previous_status,
            },
        )
        return self.get_order_details(order.id)

    def refund_order(
        self,
        order_id: int,
        amount: float | None = None,
        reason: str = "",
        current_user: User | None = None,
    ) -> OrderDetailResponse:
        """Refund a PAID online order through the Razorpay API."""
        order = self.repo.get_by_id_with_relations(order_id)
        if not order:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Order with ID {order_id} not found",
            )

        if order.payment_status != PaymentStatus.PAID.value:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only orders with PAID payment status can be refunded",
            )

        if not order.gateway_payment_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No gateway payment reference recorded for this order",
            )

        if amount is not None and amount <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Refund amount must be greater than zero",
            )

        if amount is not None and amount > float(order.total_amount or 0):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Refund amount cannot exceed the order total",
            )

        # Issue the refund through Razorpay (secret stays server-side).
        try:
            refund_result = payment_service.refund_payment(
                order.gateway_payment_id, amount
            )
        except Exception as exc:
            logger.error(
                "Razorpay refund failed for order %s: %s", order.order_number, exc
            )
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Payment gateway refund failed. Please try again.",
            )

        refund_amount = float(refund_result.get("amount", 0)) / 100
        order.payment_status = PaymentStatus.REFUNDED.value
        order.refund_id = str(refund_result.get("id") or "") or None
        order.refund_amount = refund_amount
        order.refunded_at = datetime.now(UTC).replace(tzinfo=None)
        self.db.commit()

        changed_by = current_user.full_name if current_user else "Staff"
        self.repo.add_status_history(
            order_id=order.id,
            previous_status=order.order_status,
            new_status=order.order_status,
            changed_by_name=changed_by,
            notes=(
                f"Refund of ₹{refund_amount:,.2f} issued via Razorpay "
                f"(refund_id: {refund_result.get('id')}). Reason: {reason or 'n/a'}"
            ),
        )

        emit_event(
            "order_refunded",
            {
                "id": order.id,
                "order_number": order.order_number,
                "refund_amount": refund_amount,
                "refund_id": refund_result.get("id"),
            },
        )
        return self.get_order_details(order.id)

    def get_order_stats_summary(
        self,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        platform: str | None = None,
    ) -> OrderStatusSummary:
        """Retrieve aggregated order status breakdown filtered by date range and platform."""
        counts = self.repo.get_status_counts(
            date_from=date_from,
            date_to=date_to,
            platform=platform,
        )
        return OrderStatusSummary(**counts)

    def create_website_order(
        self,
        payload: WebsiteOrderCreateRequest,
    ) -> WebsiteOrderCreateResponse:
        """Process customer order from website, link customer record, and initialize order pipeline."""
        if not payload.items:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Order must contain at least one item",
            )

        # Block orders when the website shop is closed (manual switch + schedule)
        from app.services.business_hours_service import resolve_shop_status

        shop_status = resolve_shop_status(self.db)
        if not shop_status["website_open"]:
            hours = shop_status.get("business_hours")
            detail = "We are currently CLOSED and not accepting online orders."
            if hours and not hours.is_open:
                detail = f"{hours.status_text} We are not accepting online orders right now."
                if hours.next_open_text:
                    detail += f" We open {hours.next_open_text.lower()}."
            else:
                detail += " Please check back during shop hours."
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=detail,
            )

        # Snapshot the menu food-cost onto each line so historical margin is
        # never rewritten when menu prices are later edited. Matched by
        # item name + portion size (falls back to 0 when unmatched).
        from app.models.menu import MenuItem

        cost_lookup: dict[tuple[str, str], float] = {}
        try:
            for _m in self.db.query(MenuItem).all():
                _mname = (_m.name or "").strip().lower()
                for _p in (_m.portions or []):
                    cost_lookup[
                        (_mname, (_p.portion_size or "").strip().lower())
                    ] = float(_p.cost_price or 0.0)
        except Exception:
            cost_lookup = {}

        db_items: list[OrderItem] = []
        subtotal = 0.0
        food_cost = 0.0
        summary_parts: list[str] = []

        for item_data in payload.items:
            item_total = round(item_data.unit_price * item_data.quantity, 2)
            unit_cost = cost_lookup.get(
                (
                    (item_data.item_name or "").strip().lower(),
                    (item_data.portion_size or "").strip().lower(),
                ),
                0.0,
            )
            # Complimentary promo gifts never contribute to the payable subtotal.
            if not item_data.is_free:
                subtotal += item_total
                food_cost += round(unit_cost * item_data.quantity, 2)
            summary_parts.append(
                f"{item_data.quantity}x {item_data.item_name} ({item_data.portion_size})"
                + (" [FREE]" if item_data.is_free else "")
            )

            db_items.append(
                OrderItem(
                    item_name=item_data.item_name,
                    portion_size=item_data.portion_size,
                    quantity=item_data.quantity,
                    unit_price=item_data.unit_price,
                    total_price=item_total,
                    cost_price=unit_cost,
                    is_free=item_data.is_free,
                )
            )

        # Fallback: promo-level free item (used when the storefront sends only the coupon)
        if payload.discount_type == "free_item" and payload.free_item_name:
            already_added = any(i.is_free for i in db_items)
            if not already_added:
                db_items.append(
                    OrderItem(
                        item_name=payload.free_item_name,
                        portion_size="Single",
                        quantity=1,
                        unit_price=0.0,
                        total_price=0.0,
                        is_free=True,
                    )
                )
                summary_parts.append(f"1x {payload.free_item_name} (FREE)")

        subtotal = round(subtotal, 2)

        # Pricing model (tax-inclusive / reverse calculation):
        #   Menu prices are the FINAL all-inclusive price the customer pays (e.g.
        #   a ₹149 dish). GST, the gateway fee and VAS are all *inside* that ₹149
        #   — none of them are added on top. They are only backed OUT internally
        #   for reporting & margin.
        #   Transaction fee + VAS apply to EVERY order (Online, COD, Pickup) as
        #   internal costs. The transaction-fee base is the amount that actually
        #   goes through the gateway: txn_base = (goods − discount) + delivery,
        #   so delivery raises the fee and a discount lowers it.
        #   "other_expense" is likewise internal (margin only), never charged.
        # The customer bill is simply: goods (tax-inclusive) + delivery.
        # Everything is computed here, server-side, from the CRM config so
        # the checkout total can never be tampered with client-side.
        from app.models.storefront import StorefrontConfig

        cfg = self.db.query(StorefrontConfig).first()
        txn_fee_pct = float(getattr(cfg, "transaction_fee_percent", 0.0) or 0.0)
        gst_pct = float(getattr(cfg, "gst_percent", 5.0) or 5.0)
        vas_fee = round(float(getattr(cfg, "vas_fee", 0.0) or 0.0), 2)
        other_expense = round(float(getattr(cfg, "other_expense", 0.0) or 0.0), 2)

        # Online vs offline is still needed to decide the initial payment
        # flow (online stays PENDING until Razorpay confirms), but the
        # transaction fee + VAS now apply to every order regardless.
        payment_method_upper = payload.payment_method.upper()
        is_online = (
            "ONLINE" in payment_method_upper
            or "UPI" in payment_method_upper
            or "CARD" in payment_method_upper
        )

        goods_incl = round(subtotal - payload.discount, 2)  # tax-inclusive goods
        delivery = round(payload.delivery_fee, 2)
        gst_divisor = 1 + (gst_pct / 100)
        goods_excl = round(goods_incl / gst_divisor, 2)  # GST removed
        tax = round(goods_incl - goods_excl, 2)  # GST included (report only)
        txn_base = round(goods_incl + delivery, 2)  # amount going through gateway
        transaction_fee = round(txn_base * txn_fee_pct / 100, 2)
        # The customer pays ONLY the menu price (+ delivery). The menu price
        # already includes GST and absorbs the gateway fee + VAS, so those are
        # internal costs — never added to the customer's bill.
        total_amount = round(goods_incl + delivery, 2)
        # Net margin contribution (analytics): total charged − GST − fees − food
        margin_contribution = round(
            total_amount - tax - transaction_fee - vas_fee - other_expense - food_cost,
            2,
        )

        # Auto-create or link customer
        customer = self.repo.get_or_create_customer(
            name=payload.customer.name,
            phone=payload.customer.phone,
            email=payload.customer.email,
            address=payload.customer.delivery_address,
            order_amount=total_amount,
        )

        order_number = self.repo.generate_next_order_number(OrderPlatform.WEBSITE.value)

        if is_online:
            # Online orders start PENDING and only become PAID/CONFIRMED
            # after the Razorpay payment is verified (via /payments/verify
            # or the Razorpay webhook). This prevents confirming orders
            # before real money is received.
            payment_status = PaymentStatus.PENDING.value
            initial_status = OrderStatus.NEW.value
            initial_note = f"Online order placed via Website ({payload.payment_method}) - awaiting payment confirmation"
        else:
            payment_status = PaymentStatus.PENDING.value
            initial_status = OrderStatus.NEW.value
            initial_note = "Cash on Delivery order placed via Website"

        order = Order(
            order_number=order_number,
            platform=OrderPlatform.WEBSITE.value,
            customer_id=customer.id,
            customer_name=payload.customer.name,
            customer_phone=payload.customer.phone,
            delivery_address=payload.customer.delivery_address or customer.default_address,
            subtotal=subtotal,
            discount=payload.discount,
            delivery_fee=payload.delivery_fee,
            order_type=(payload.order_type or "").upper() or None,
            transaction_fee=transaction_fee,
            vas_fee=vas_fee,
            other_expense=other_expense,
            tax=tax,
            total_amount=total_amount,
            order_status=initial_status,
            payment_status=payment_status,
            items_summary=", ".join(summary_parts)[:490],
            notes=payload.notes,
            items=db_items,
        )

        self.db.add(order)
        self.db.commit()
        self.db.refresh(order)

        self.repo.add_status_history(
            order_id=order.id,
            previous_status=None,
            new_status=initial_status,
            changed_by_name="Website Customer",
            notes=initial_note,
        )

        logger.info(f"Website Order #{order_number} created for {payload.customer.name} (Amount: Rs.{total_amount})")

        emit_event(
            "new_order",
            {
                "id": order.id,
                "order_number": order.order_number,
                "platform": order.platform,
                "customer_name": order.customer_name,
                "total_amount": order.total_amount,
                "items_summary": order.items_summary,
                "order_status": order.order_status,
            },
        )

        return WebsiteOrderCreateResponse(
            order_number=order.order_number,
            order_status=order.order_status,
            payment_status=order.payment_status,
            subtotal=order.subtotal,
            discount=order.discount,
            delivery_fee=order.delivery_fee,
            transaction_fee=order.transaction_fee,
            vas_fee=order.vas_fee,
            tax=order.tax,
            total_amount=order.total_amount,
            estimated_delivery_minutes=35,
            tracking_token=f"trk_{order.id}_{order.order_number.lower().replace('-', '')}",
            created_at=order.created_at,
        )

    def track_public_order(self, order_number: str) -> PublicOrderTrackResponse:
        """Publicly track order status without exposing internal notes or financial margins."""
        clean_num = order_number.strip().upper()
        order = self.repo.get_by_order_number(clean_num)
        if not order:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Order '{order_number}' not found",
            )

        phone = order.customer_phone or ""
        if len(phone) >= 10:
            masked_phone = phone[:3] + "****" + phone[-4:]
        else:
            masked_phone = phone[:2] + "***" + phone[-2:] if len(phone) > 4 else "***"

        stages = [
            ("NEW", "Order Received", "Your order has been received by Panna Kitchen"),
            ("CONFIRMED", "Confirmed", "Order confirmed & scheduled for cooking"),
            ("PREPARING", "Cooking in Handi", "Chef is sealing the biryani handi on dum"),
            ("READY", "Packed & Ready", "Packed hot in sealed insulated containers"),
            ("OUT_FOR_DELIVERY", "Out for Delivery", "Delivery partner picked up your order"),
            ("DELIVERED", "Delivered", "Delivered hot and fresh. Enjoy your biryani!"),
        ]

        stage_order = {s[0]: i for i, s in enumerate(stages)}
        curr_idx = stage_order.get(order.order_status, 0)
        is_cancelled = order.order_status == OrderStatus.CANCELLED.value

        history_map = {h.new_status: h.created_at for h in order.status_history}
        timeline: list[TrackingTimelineStep] = []

        for idx, (st_key, label, desc) in enumerate(stages):
            is_completed = (not is_cancelled) and (idx <= curr_idx)
            is_current = (not is_cancelled) and (idx == curr_idx)
            step_time = history_map.get(st_key) or (order.created_at if idx == 0 else None)

            timeline.append(
                TrackingTimelineStep(
                    step_key=st_key,
                    label=label,
                    description=desc,
                    completed=is_completed,
                    current=is_current,
                    timestamp=step_time if is_completed else None,
                )
            )

        status_display = "Order Cancelled" if is_cancelled else stages[curr_idx][1]

        return PublicOrderTrackResponse(
            order_number=order.order_number,
            order_status=order.order_status,
            status_display=status_display,
            payment_status=order.payment_status,
            customer_name=order.customer_name,
            customer_phone_masked=masked_phone,
            delivery_address=order.delivery_address or "",
            items_summary=order.items_summary or "",
            items_count=len(order.items),
            total_amount=order.total_amount,
            created_at=order.created_at,
            estimated_delivery_minutes=35
            if order.order_status in ["NEW", "CONFIRMED", "PREPARING"]
            else (15 if order.order_status in ["READY", "OUT_FOR_DELIVERY"] else 0),
            timeline=timeline,
        )

    def process_payment_webhook(
        self,
        order_number: str,
        payload: PaymentWebhookRequest,
    ) -> PaymentWebhookResponse:
        """Handle incoming payment gateway callbacks (Razorpay/UPI)."""
        clean_num = order_number.strip().upper()
        order = self.repo.get_by_order_number(clean_num)
        if not order:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Order '{order_number}' not found",
            )

        prev_payment_status = order.payment_status
        new_payment_status = payload.payment_status.upper()
        order.payment_status = new_payment_status

        # Record the gateway + transaction reference so a refund can be
        # issued later through the Razorpay API.
        if payload.payment_gateway:
            order.gateway = payload.payment_gateway.upper()
        if payload.transaction_id:
            order.gateway_payment_id = payload.transaction_id
        # The gateway order id is carried in the notes as "Razorpay order order_xxx";
        # lift it out so the CRM can show the full transaction trail.
        if payload.notes and "razorpay order " in payload.notes.lower():
            token = payload.notes.lower().split("razorpay order ", 1)[1].strip().split()[0]
            if token:
                order.gateway_order_id = token

        auto_advanced = False
        if new_payment_status == PaymentStatus.PAID.value and order.order_status == OrderStatus.NEW.value:
            order.order_status = OrderStatus.CONFIRMED.value
            auto_advanced = True

        self.db.commit()

        # Send a WhatsApp confirmation to the customer the first time the
        # payment flips to PAID. Best-effort: a failure here must never
        # break the webhook/verify response.
        if new_payment_status == PaymentStatus.PAID.value and prev_payment_status != PaymentStatus.PAID.value:
            try:
                from app.services.whatsapp_service import (
                    format_order_confirmation,
                    whatsapp_service,
                )

                msg = format_order_confirmation(
                    order_number=order.order_number,
                    customer_name=order.customer_name or "Customer",
                    total_amount=float(order.total_amount or 0),
                    items_summary=order.items_summary or "Your order",
                    delivery_address=order.delivery_address or "",
                    eta_minutes=35,
                )
                whatsapp_service.send_text(order.customer_phone or "", msg)
            except Exception as exc:  # pragma: no cover - non-critical
                logger.warning("WhatsApp order confirmation failed: %s", exc)

        note_text = f"Payment Webhook: {new_payment_status} via {payload.payment_gateway}"
        if payload.transaction_id:
            note_text += f" (Txn: {payload.transaction_id})"
        if payload.notes:
            note_text += f" - {payload.notes}"

        self.repo.add_status_history(
            order_id=order.id,
            previous_status=OrderStatus.NEW.value if auto_advanced else order.order_status,
            new_status=order.order_status,
            changed_by_name="Payment Gateway Webhook",
            notes=note_text,
        )

        return PaymentWebhookResponse(
            success=True,
            order_number=order.order_number,
            previous_payment_status=prev_payment_status,
            new_payment_status=new_payment_status,
            order_status=order.order_status,
            message=f"Payment status updated to {new_payment_status}",
        )
