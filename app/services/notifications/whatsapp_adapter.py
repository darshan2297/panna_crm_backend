import urllib.parse
from datetime import UTC, datetime
from typing import Any

from app.services.notifications.base_adapter import BaseNotificationAdapter


class WhatsAppNotificationAdapter(BaseNotificationAdapter):
    """
    WhatsApp Adapter for kitchen low-stock & restock alerts.
    Generates structured WhatsApp markdown messages and clickable https://wa.me/ links.
    """

    DEFAULT_KITCHEN_PHONE = "+919876543210"

    def format_message(
        self,
        title: str,
        message: str,
        severity: str,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        icon = "🚨" if severity == "CRITICAL" else "⚠️" if severity == "WARNING" else "ℹ️"
        lines = [
            f"{icon} *PANNA BIRYANI — KITCHEN ALERT* {icon}",
            f"*Severity:* _{severity.upper()}_",
            f"*Subject:* *{title}*",
            "",
            message,
        ]

        if metadata:
            lines.append("")
            lines.append("📊 *Stock Details:*")
            if "item_name" in metadata:
                lines.append(f"• *Item:* {metadata['item_name']} ({metadata.get('sku', 'N/A')})")
            if "current_stock" in metadata and "unit" in metadata:
                lines.append(f"• *Current Balance:* {metadata['current_stock']} {metadata['unit']}")
            if "reorder_level" in metadata and "unit" in metadata:
                lines.append(f"• *Safety Threshold:* {metadata['reorder_level']} {metadata['unit']}")
            if "suggested_qty" in metadata and "unit" in metadata:
                lines.append(f"• *Suggested Reorder:* {metadata['suggested_qty']} {metadata['unit']}")
            if "supplier" in metadata:
                lines.append(f"• *Supplier:* {metadata['supplier']}")
            if "estimated_cost" in metadata:
                lines.append(f"• *Est. Cost:* ₹{metadata['estimated_cost']:,.2f}")

        lines.append("")
        lines.append(f"_Generated at: {datetime.now(UTC).strftime('%d %b %Y, %I:%M %p UTC')}_")
        lines.append("👉 _Please login to Panna CRM to approve Restock Purchase Order._")

        return "\n".join(lines)

    def dispatch(
        self,
        title: str,
        message: str,
        severity: str,
        recipient: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        target_phone = recipient or self.DEFAULT_KITCHEN_PHONE
        # Sanitize phone: remove +, spaces, dashes
        clean_phone = "".join(filter(str.isdigit, target_phone))
        if not clean_phone.startswith("91") and len(clean_phone) == 10:
            clean_phone = f"91{clean_phone}"

        formatted_text = self.format_message(title, message, severity, metadata)
        encoded_text = urllib.parse.quote(formatted_text)
        wa_url = f"https://wa.me/{clean_phone}?text={encoded_text}"

        return {
            "channel": "WHATSAPP",
            "recipient": target_phone,
            "status": "MOCK_DELIVERED",
            "preview_content": formatted_text,
            "action_url": wa_url,
            "dispatched_at": datetime.now(UTC),
        }
