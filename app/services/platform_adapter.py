from abc import ABC, abstractmethod
from typing import Any

from app.models.order import OrderPlatform, OrderStatus, PaymentStatus


class PlatformAdapter(ABC):
    """
    Abstract Platform Adapter.
    Enforces a clean abstraction for order ingestion and platform-specific behaviors
    across Panna Website, Zomato, Swiggy, and future food delivery channels.
    """

    @property
    @abstractmethod
    def platform(self) -> OrderPlatform:
        pass

    @property
    @abstractmethod
    def display_name(self) -> str:
        pass

    @property
    @abstractmethod
    def default_commission_rate(self) -> float:
        """Commission percentage (e.g. 0.0 for direct website, 0.20 for 20%)."""
        pass

    @abstractmethod
    def format_order_number(self, identifier: str | int) -> str:
        """Generate standardized order reference number for platform."""
        pass

    @abstractmethod
    def normalize_payload(self, raw_data: dict[str, Any]) -> dict[str, Any]:
        """Convert platform-specific raw webhook / request payload to canonical format."""
        pass

    def validate_order(self, data: dict[str, Any]) -> tuple[bool, str | None]:
        """Validate that all required order information is present."""
        if not data.get("customer_name"):
            return False, "Customer name is required"
        if not data.get("customer_phone"):
            return False, "Customer phone number is required"
        items = data.get("items")
        if not items or len(items) == 0:
            return False, "Order must contain at least one item"
        return True, None

    def calculate_commission(self, total_amount: float) -> float:
        """Estimate platform commission cut."""
        return round(total_amount * self.default_commission_rate, 2)


class WebsiteAdapter(PlatformAdapter):
    """Adapter for Panna Direct Website and in-house phone/walk-in orders."""

    @property
    def platform(self) -> OrderPlatform:
        return OrderPlatform.WEBSITE

    @property
    def display_name(self) -> str:
        return "Panna Website / Direct"

    @property
    def default_commission_rate(self) -> float:
        return 0.0  # 0% commission on direct website orders

    def format_order_number(self, identifier: str | int) -> str:
        return f"PB-W-{identifier}"

    def normalize_payload(self, raw_data: dict[str, Any]) -> dict[str, Any]:
        return {
            "platform": OrderPlatform.WEBSITE.value,
            "customer_name": raw_data.get("customer_name", "").strip(),
            "customer_phone": raw_data.get("customer_phone", "").strip(),
            "delivery_address": raw_data.get("delivery_address", "Pickup / Direct Counter"),
            "items": raw_data.get("items", []),
            "subtotal": float(raw_data.get("subtotal", 0.0)),
            "discount": float(raw_data.get("discount", 0.0)),
            "delivery_fee": float(raw_data.get("delivery_fee", 0.0)),
            "tax": float(raw_data.get("tax", 0.0)),
            "total_amount": float(raw_data.get("total_amount", 0.0)),
            "payment_status": raw_data.get("payment_status", PaymentStatus.PAID.value),
            "order_status": raw_data.get("order_status", OrderStatus.NEW.value),
            "notes": raw_data.get("notes"),
        }


class ZomatoAdapter(PlatformAdapter):
    """Adapter for Zomato merchant webhook and simulated aggregator orders."""

    @property
    def platform(self) -> OrderPlatform:
        return OrderPlatform.ZOMATO

    @property
    def display_name(self) -> str:
        return "Zomato"

    @property
    def default_commission_rate(self) -> float:
        return 0.22  # Typical 22% Zomato commission

    def format_order_number(self, identifier: str | int) -> str:
        return f"PB-Z-{identifier}"

    def normalize_payload(self, raw_data: dict[str, Any]) -> dict[str, Any]:
        # Maps Zomato order structure (such as external order ID) into canonical format
        ext_id = raw_data.get("order_id") or raw_data.get("zomato_order_id")
        return {
            "platform": OrderPlatform.ZOMATO.value,
            "external_order_id": str(ext_id) if ext_id else None,
            "customer_name": raw_data.get("customer_name") or raw_data.get("rider_name", "Zomato Customer"),
            "customer_phone": raw_data.get("customer_phone") or "+91 9999900000",
            "delivery_address": raw_data.get("delivery_address", "Zomato Delivery Fleet"),
            "items": raw_data.get("items", []),
            "subtotal": float(raw_data.get("subtotal", 0.0)),
            "discount": float(raw_data.get("discount", 0.0)),
            "delivery_fee": float(raw_data.get("delivery_fee", 0.0)),
            "tax": float(raw_data.get("tax", 0.0)),
            "total_amount": float(raw_data.get("total_amount", 0.0)),
            "payment_status": raw_data.get("payment_status", PaymentStatus.PAID.value),
            "order_status": raw_data.get("order_status", OrderStatus.CONFIRMED.value),
            "notes": raw_data.get("notes") or raw_data.get("special_instructions"),
        }


class SwiggyAdapter(PlatformAdapter):
    """Adapter for Swiggy merchant partner webhook and simulated orders."""

    @property
    def platform(self) -> OrderPlatform:
        return OrderPlatform.SWIGGY

    @property
    def display_name(self) -> str:
        return "Swiggy"

    @property
    def default_commission_rate(self) -> float:
        return 0.20  # Typical 20% Swiggy commission

    def format_order_number(self, identifier: str | int) -> str:
        return f"PB-S-{identifier}"

    def normalize_payload(self, raw_data: dict[str, Any]) -> dict[str, Any]:
        ext_id = raw_data.get("order_id") or raw_data.get("swiggy_order_id")
        return {
            "platform": OrderPlatform.SWIGGY.value,
            "external_order_id": str(ext_id) if ext_id else None,
            "customer_name": raw_data.get("customer_name") or "Swiggy Customer",
            "customer_phone": raw_data.get("customer_phone") or "+91 8888800000",
            "delivery_address": raw_data.get("delivery_address", "Swiggy Delivery Partner"),
            "items": raw_data.get("items", []),
            "subtotal": float(raw_data.get("subtotal", 0.0)),
            "discount": float(raw_data.get("discount", 0.0)),
            "delivery_fee": float(raw_data.get("delivery_fee", 0.0)),
            "tax": float(raw_data.get("tax", 0.0)),
            "total_amount": float(raw_data.get("total_amount", 0.0)),
            "payment_status": raw_data.get("payment_status", PaymentStatus.PAID.value),
            "order_status": raw_data.get("order_status", OrderStatus.CONFIRMED.value),
            "notes": raw_data.get("notes") or raw_data.get("delivery_notes"),
        }


# Registry of platform adapters
_ADAPTERS: dict[OrderPlatform, PlatformAdapter] = {
    OrderPlatform.WEBSITE: WebsiteAdapter(),
    OrderPlatform.ZOMATO: ZomatoAdapter(),
    OrderPlatform.SWIGGY: SwiggyAdapter(),
}


def get_platform_adapter(platform: str | OrderPlatform) -> PlatformAdapter:
    """Retrieve the appropriate platform adapter."""
    if isinstance(platform, str):
        try:
            platform_enum = OrderPlatform(platform.upper())
        except ValueError:
            platform_enum = OrderPlatform.WEBSITE
    else:
        platform_enum = platform

    return _ADAPTERS.get(platform_enum, _ADAPTERS[OrderPlatform.WEBSITE])
