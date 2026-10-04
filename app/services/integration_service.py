import json
import random
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from app.models.customer import Customer, CustomerSegment
from app.models.integration import (
    IntegrationConfig,
    IntegrationLog,
)
from app.models.order import Order, OrderItem, OrderStatus, PaymentStatus
from app.schemas.integrations import (
    IntegrationConfigRead,
    IntegrationConfigUpdate,
    IntegrationHealthSummary,
    IntegrationLogRead,
    WebhookSimulateRequest,
)
from app.socket_manager import emit_event


class IntegrationService:
    def __init__(self, db: Session):
        self.db = db
        self._ensure_default_configs()

    def _ensure_default_configs(self):
        defaults = [
            {
                "platform": "ZOMATO",
                "is_enabled": True,
                "store_id": "ZOM-PUN-0842",
                "api_key_masked": "zom_live_***...98a2",
                "webhook_secret": "whsec_zom_982341",
                "auto_accept": True,
                "environment": "LIVE",
                "status": "CONNECTED",
                "orders_synced_today": 18,
            },
            {
                "platform": "SWIGGY",
                "is_enabled": True,
                "store_id": "SWG-VIMAN-421",
                "api_key_masked": "swg_live_***...71e4",
                "webhook_secret": "whsec_swg_441029",
                "auto_accept": True,
                "environment": "LIVE",
                "status": "CONNECTED",
                "orders_synced_today": 24,
            },
            {
                "platform": "WEBSITE",
                "is_enabled": True,
                "store_id": "PANNA-DIRECT-WEB",
                "api_key_masked": "pan_direct_***...2901",
                "webhook_secret": "whsec_pan_direct",
                "auto_accept": True,
                "environment": "LIVE",
                "status": "CONNECTED",
                "orders_synced_today": 31,
            },
            {
                "platform": "ONDC",
                "is_enabled": False,
                "store_id": "ONDC-BAP-9901",
                "api_key_masked": "ondc_sand_***...1102",
                "webhook_secret": "whsec_ondc_test",
                "auto_accept": False,
                "environment": "SANDBOX",
                "status": "DISCONNECTED",
                "orders_synced_today": 0,
            },
        ]

        for d in defaults:
            cfg = self.db.query(IntegrationConfig).filter(IntegrationConfig.platform == d["platform"]).first()
            if not cfg:
                new_cfg = IntegrationConfig(
                    platform=d["platform"],
                    is_enabled=d["is_enabled"],
                    store_id=d["store_id"],
                    api_key_masked=d["api_key_masked"],
                    webhook_secret=d["webhook_secret"],
                    auto_accept=d["auto_accept"],
                    environment=d["environment"],
                    status=d["status"],
                    orders_synced_today=d["orders_synced_today"],
                    shop_open=True,
                    last_sync_at=datetime.now(UTC),
                )
                self.db.add(new_cfg)
        self.db.commit()

    def get_health_summary(self) -> IntegrationHealthSummary:
        configs = self.db.query(IntegrationConfig).all()
        active_cnt = sum(1 for c in configs if c.is_enabled and c.status == "CONNECTED")
        synced_today = sum(c.orders_synced_today for c in configs)
        overall = "HEALTHY" if active_cnt >= 2 else "WARNING"

        return IntegrationHealthSummary(
            platforms=[IntegrationConfigRead.from_orm(c) for c in configs],
            overall_status=overall,
            total_synced_today=synced_today,
            active_platforms_count=active_cnt,
        )

    def update_config(self, platform: str, payload: IntegrationConfigUpdate) -> IntegrationConfigRead:
        cfg = self.db.query(IntegrationConfig).filter(IntegrationConfig.platform == platform.upper()).first()
        if not cfg:
            raise ValueError(f"Integration config for {platform} not found")

        if payload.is_enabled is not None:
            cfg.is_enabled = payload.is_enabled
            if not cfg.is_enabled:
                cfg.status = "DISCONNECTED"
            else:
                cfg.status = "CONNECTED"

        if payload.store_id is not None:
            cfg.store_id = payload.store_id

        if payload.api_key:
            masked = payload.api_key[:8] + "***..." + payload.api_key[-4:] if len(payload.api_key) > 12 else "***"
            cfg.api_key_masked = masked

        if payload.webhook_secret is not None:
            cfg.webhook_secret = payload.webhook_secret

        if payload.auto_accept is not None:
            cfg.auto_accept = payload.auto_accept

        if payload.environment is not None:
            cfg.environment = payload.environment

        if payload.sync_interval_minutes is not None:
            cfg.sync_interval_minutes = payload.sync_interval_minutes

        if payload.shop_open is not None:
            cfg.shop_open = payload.shop_open

        self.db.commit()
        self.db.refresh(cfg)

        if payload.shop_open is not None:
            emit_event(
                "shop_status_changed",
                {"platform": platform.upper(), "shop_open": cfg.shop_open},
            )

        # Log change
        self.log_event(
            platform=platform.upper(),
            event_type="CONFIG_UPDATED",
            status="SUCCESS",
            message=f"Settings updated for {platform}",
            payload={"environment": cfg.environment, "auto_accept": cfg.auto_accept},
        )

        return IntegrationConfigRead.from_orm(cfg)

    def trigger_sync(self, platform: str) -> dict[str, Any]:
        cfg = self.db.query(IntegrationConfig).filter(IntegrationConfig.platform == platform.upper()).first()
        if not cfg:
            raise ValueError(f"Platform {platform} not found")

        cfg.last_sync_at = datetime.now(UTC)
        pulled_orders = random.randint(1, 4)
        cfg.orders_synced_today += pulled_orders
        cfg.status = "CONNECTED"
        self.db.commit()

        msg = f"Manual sync completed. Pulled {pulled_orders} pending orders from {platform} partner API."
        self.log_event(
            platform=platform.upper(),
            event_type="SYNC_ORDERS",
            status="SUCCESS",
            message=msg,
            payload={"pulled_orders": pulled_orders},
        )

        return {
            "success": True,
            "platform": platform.upper(),
            "orders_pulled": pulled_orders,
            "synced_at": cfg.last_sync_at.isoformat(),
            "message": msg,
        }

    def process_webhook(self, platform: str, payload: dict[str, Any]) -> dict[str, Any]:
        platform_upper = platform.upper()
        event_type = payload.get("event", "ORDER_PLACED")

        # Record log
        self.log_event(
            platform=platform_upper,
            event_type=f"WEBHOOK_{event_type}",
            status="SUCCESS",
            message=f"Webhook event '{event_type}' received from {platform_upper}",
            payload=payload,
        )

        cfg = self.db.query(IntegrationConfig).filter(IntegrationConfig.platform == platform_upper).first()
        if cfg:
            cfg.orders_synced_today += 1
            cfg.last_sync_at = datetime.now(UTC)
            self.db.commit()

        # If shop is closed, reject incoming order intake events
        if cfg and not cfg.shop_open and event_type in ("ORDER_PLACED", "ORDER_CREATED"):
            return {
                "success": False,
                "message": f"Shop is currently CLOSED on {platform_upper}. Incoming order rejected.",
                "event": event_type,
                "received_at": datetime.now(UTC).isoformat(),
            }

        return {
            "success": True,
            "message": f"Webhook processed successfully for {platform_upper}",
            "event": event_type,
            "received_at": datetime.now(UTC).isoformat(),
        }

    def simulate_webhook_order(self, req: WebhookSimulateRequest) -> dict[str, Any]:
        platform = req.platform.upper()
        order_num = f"{platform[:3]}-{random.randint(100000, 999999)}"

        # Reject incoming orders when shop is closed on that platform
        closed_cfg = self.db.query(IntegrationConfig).filter(IntegrationConfig.platform == platform).first()
        if closed_cfg and not closed_cfg.shop_open:
            from fastapi import HTTPException
            from fastapi import status as _status

            raise HTTPException(
                status_code=_status.HTTP_403_FORBIDDEN,
                detail=f"Shop is currently CLOSED on {platform}. Order rejected. Re-open the shop to accept orders.",
            )

        # Find or create customer
        phone = req.customer_phone or "9876543210"
        customer = self.db.query(Customer).filter(Customer.phone == phone).first()
        if not customer:
            customer = Customer(
                name=req.customer_name or "Partner App Customer",
                phone=phone,
                default_address=req.delivery_address or "Kalyani Nagar, Pune",
                segment=CustomerSegment.NEW.value,
                total_orders=1,
                total_spent=req.total_amount or 450.0,
                last_order_date=datetime.now(UTC),
            )
            self.db.add(customer)
            self.db.flush()
        else:
            customer.total_orders += 1
            customer.total_spent += req.total_amount or 450.0
            customer.last_order_date = datetime.now(UTC)

        items_summary = []
        subtotal = 0.0

        items_to_create = req.items or [
            {"item_name": "Chicken Dum Biryani", "quantity": 1, "unit_price": 380.0},
            {"item_name": "Mirchi Ka Salan", "quantity": 1, "unit_price": 70.0},
        ]

        parsed_items = []
        for item_data in items_to_create:
            if isinstance(item_data, dict):
                iname = item_data.get("item_name", "Biryani")
                qty = int(item_data.get("quantity", 1))
                price = float(item_data.get("unit_price", 350.0))
            else:
                iname = item_data.item_name
                qty = item_data.quantity
                price = item_data.unit_price

            tot = price * qty
            subtotal += tot
            items_summary.append(f"{qty}x {iname}")
            parsed_items.append((iname, qty, price, tot))

        tax = round(subtotal * 0.05, 2)
        delivery_fee = 40.0
        total_amount = req.total_amount if req.total_amount else round(subtotal + tax + delivery_fee, 2)

        order = Order(
            order_number=order_num,
            platform=platform,
            customer_id=customer.id,
            customer_name=customer.name,
            customer_phone=customer.phone,
            delivery_address=req.delivery_address or "Kalyani Nagar, Pune",
            subtotal=subtotal,
            discount=0.0,
            delivery_fee=delivery_fee,
            tax=tax,
            total_amount=total_amount,
            order_status=OrderStatus.CONFIRMED.value,
            payment_status=PaymentStatus.PAID.value,
            items_summary=", ".join(items_summary),
            notes=f"Auto-ingested from {platform} partner webhook simulation",
        )
        self.db.add(order)
        self.db.flush()

        for iname, qty, price, tot in parsed_items:
            o_item = OrderItem(
                order_id=order.id,
                item_name=iname,
                portion_size="500g",
                quantity=qty,
                unit_price=price,
                total_price=tot,
            )
            self.db.add(o_item)

        # Update integration stats
        cfg = self.db.query(IntegrationConfig).filter(IntegrationConfig.platform == platform).first()
        if cfg:
            cfg.orders_synced_today += 1
            cfg.last_sync_at = datetime.now(UTC)

        # Log event
        self.log_event(
            platform=platform,
            event_type="WEBHOOK_ORDER_CREATED",
            status="SUCCESS",
            message=f"Order {order_num} created via simulated {platform} webhook",
            payload={"order_number": order_num, "amount": order.total_amount, "customer": customer.name},
        )

        self.db.commit()

        emit_event(
            "new_order",
            {
                "id": order.id,
                "order_number": order.order_number,
                "platform": platform,
                "customer_name": customer.name,
                "total_amount": order.total_amount,
                "items_summary": order.items_summary,
                "order_status": order.order_status,
            },
        )

        return {
            "success": True,
            "order_number": order_num,
            "order_id": order.id,
            "platform": platform,
            "total_amount": order.total_amount,
            "items_summary": order.items_summary,
            "message": f"Successfully simulated incoming order from {platform}",
        }

    def log_event(self, platform: str, event_type: str, status: str, message: str, payload: Any | None = None):
        snippet = None
        if payload:
            snippet = json.dumps(payload)[:500] if not isinstance(payload, str) else payload[:500]
        log = IntegrationLog(
            platform=platform,
            event_type=event_type,
            status=status,
            message=message,
            payload_snippet=snippet,
        )
        self.db.add(log)
        self.db.commit()

    def get_recent_logs(self, limit: int = 50) -> list[IntegrationLogRead]:
        logs = self.db.query(IntegrationLog).order_by(IntegrationLog.created_at.desc()).limit(limit).all()
        return [IntegrationLogRead.from_orm(log) for log in logs]
