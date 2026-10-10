"""
WhatsApp messaging service (Gupshup / BSP).

Sends messages through the Gupshup WhatsApp API when an API key is
configured. Falls back to a `wa.me` deep link when the gateway is
disabled or the send fails, so the customer always gets a working
action.

NOTE: WhatsApp business-initiated messages (order confirmations,
alerts) require a Meta-approved *template*. Free-form text only
works inside a 24h customer-service window after the customer
messages the business first. Create templates in the Gupshup
dashboard and reference them by `template_name`.
"""

import logging
import urllib.parse
from datetime import UTC, datetime
from typing import Any

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


class WhatsAppService:
    def __init__(self) -> None:
        self.api_key = (settings.WHATSAPP_API_KEY or "").strip()
        self.api_url = settings.WHATSAPP_API_URL or "https://api.gupshup.io/sm/api/v1/msg"
        self.sender_id = (settings.WHATSAPP_SENDER_ID or "").strip()

    @property
    def enabled(self) -> bool:
        """True when an API key is configured."""
        return bool(self.api_key)

    @staticmethod
    def normalize_phone(phone: str) -> str:
        """Strip non-digits and prefix with 91 if a 10-digit Indian number."""
        clean = "".join(filter(str.isdigit, phone or ""))
        if not clean.startswith("91") and len(clean) == 10:
            clean = f"91{clean}"
        return clean

    @staticmethod
    def wa_me_link(phone: str, text: str) -> str:
        clean = WhatsAppService.normalize_phone(phone)
        return f"https://wa.me/{clean}?text={urllib.parse.quote(text)}"

    def send_text(self, phone: str, message: str) -> dict[str, Any]:
        """Send a plain text WhatsApp message via Gupshup.

        Returns a result dict with `status` of DELIVERED / LINK_GENERATED
        / FAILED and an `action_url` (wa.me fallback) the caller can use.
        """
        destination = self.normalize_phone(phone)
        if not self.enabled:
            return {
                "status": "LINK_GENERATED",
                "action_url": self.wa_me_link(phone, message),
                "message": "WhatsApp API key not configured; using wa.me link",
            }

        body: dict[str, Any] = {
            "channel": "whatsapp",
            "destination": destination,
            "message": message,
            "source": self.sender_id or destination,
        }
        # Gupshup expects src.name for the sender display name.
        if self.sender_id:
            body["src.name"] = "Panna Biryani"

        try:
            resp = httpx.post(
                self.api_url,
                headers={
                    "apikey": self.api_key,
                    "Content-Type": "application/json",
                },
                json=body,
                timeout=20.0,
            )
        except httpx.HTTPError as exc:
            logger.error("Gupshup WhatsApp send failed: %s", exc)
            return {
                "status": "LINK_GENERATED",
                "action_url": self.wa_me_link(phone, message),
                "message": f"Gateway error: {exc}; using wa.me link",
            }

        if resp.status_code >= 400:
            logger.error(
                "Gupshup WhatsApp send rejected (%s): %s",
                resp.status_code,
                resp.text[:500],
            )
            return {
                "status": "LINK_GENERATED",
                "action_url": self.wa_me_link(phone, message),
                "message": f"Gateway rejected ({resp.status_code}); using wa.me link",
            }

        data = resp.json()
        return {
            "status": "DELIVERED",
            "action_url": None,
            "provider_message_id": data.get("messageId") or data.get("id"),
            "message": "Message sent via Gupshup",
            "raw": data,
        }

    def send_template(
        self,
        phone: str,
        template_name: str,
        params: list[str] | None = None,
    ) -> dict[str, Any]:
        """Send a Meta-approved WhatsApp template.

        `params` are the dynamic values substituted into the template,
        in the order declared in the Gupshup template.
        """
        destination = self.normalize_phone(phone)
        if not self.enabled:
            return {
                "status": "LINK_GENERATED",
                "action_url": self.wa_me_link(phone, ""),
                "message": "WhatsApp API key not configured",
            }

        template_params = params or []
        body: dict[str, Any] = {
            "channel": "whatsapp",
            "destination": destination,
            "source": self.sender_id or destination,
            "template": template_name,
        }
        if template_params:
            body["params"] = template_params

        try:
            resp = httpx.post(
                self.api_url,
                headers={
                    "apikey": self.api_key,
                    "Content-Type": "application/json",
                },
                json=body,
                timeout=20.0,
            )
        except httpx.HTTPError as exc:
            logger.error("Gupshup template send failed: %s", exc)
            return {
                "status": "LINK_GENERATED",
                "action_url": self.wa_me_link(phone, ""),
                "message": f"Gateway error: {exc}",
            }

        if resp.status_code >= 400:
            logger.error(
                "Gupshup template send rejected (%s): %s",
                resp.status_code,
                resp.text[:500],
            )
            return {
                "status": "LINK_GENERATED",
                "action_url": self.wa_me_link(phone, ""),
                "message": f"Gateway rejected ({resp.status_code})",
            }

        data = resp.json()
        return {
            "status": "DELIVERED",
            "action_url": None,
            "provider_message_id": data.get("messageId") or data.get("id"),
            "message": f"Template '{template_name}' sent",
            "raw": data,
        }


whatsapp_service = WhatsAppService()


def format_order_confirmation(
    order_number: str,
    customer_name: str,
    total_amount: float,
    items_summary: str,
    delivery_address: str = "",
    eta_minutes: int = 35,
) -> str:
    """Build the plain-text order confirmation message."""
    lines = [
        "🥘 *PANNA BIRYANI — Order Confirmed!* 🥘",
        "",
        f"*Order:* {order_number}",
        f"*Name:* {customer_name}",
        f"*Items:* {items_summary}",
        f"*Total:* ₹{total_amount:,.2f}",
        f"*ETA:* ~{eta_minutes} minutes",
    ]
    if delivery_address:
        lines.append(f"*Deliver to:* {delivery_address}")
    lines += [
        "",
        "Thank you for choosing Panna Biryani! 🍚",
        "Track your order anytime on our website.",
    ]
    return "\n".join(lines)


def now_utc_iso() -> str:
    return datetime.now(UTC).isoformat()
