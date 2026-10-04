import urllib.parse
from datetime import UTC, datetime
from typing import Any

from app.services.notifications.base_adapter import BaseNotificationAdapter


class EmailNotificationAdapter(BaseNotificationAdapter):
    """
    Email Notification Adapter for kitchen low-stock digests & critical alerts.
    Formats HTML responsive emails with brand colors (#0C3823, #D4AF37).
    """

    DEFAULT_ADMIN_EMAIL = "kitchen-ops@pannabiryani.com"

    def format_message(
        self,
        title: str,
        message: str,
        severity: str,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        color_accent = "#dc2626" if severity == "CRITICAL" else "#d97706" if severity == "WARNING" else "#0C3823"

        html_parts = [
            f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #FAF8F5; margin: 0; padding: 20px; }}
    .card {{ max-width: 600px; margin: 0 auto; background: #ffffff; border-radius: 16px; border: 1px solid #e7e5e4; overflow: hidden; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05); }}
    .header {{ background-color: #0C3823; padding: 24px; text-align: center; color: #ffffff; border-bottom: 3px solid #D4AF37; }}
    .header h1 {{ margin: 0; font-size: 20px; font-weight: 700; letter-spacing: 0.5px; }}
    .badge {{ display: inline-block; padding: 4px 12px; border-radius: 9999px; font-size: 11px; font-weight: 700; color: #ffffff; background: {color_accent}; margin-top: 8px; text-transform: uppercase; }}
    .content {{ padding: 24px; color: #1c1917; }}
    .title {{ font-size: 18px; font-weight: 700; margin-bottom: 12px; color: #0C3823; }}
    .message {{ font-size: 14px; line-height: 1.6; color: #44403c; margin-bottom: 20px; }}
    .table {{ width: 100%; border-collapse: collapse; margin-top: 16px; font-size: 13px; }}
    .table th {{ background: #f5f5f4; text-align: left; padding: 8px 12px; color: #57534e; }}
    .table td {{ padding: 10px 12px; border-bottom: 1px solid #f5f5f4; color: #1c1917; }}
    .footer {{ background: #f5f5f4; padding: 16px 24px; text-align: center; font-size: 12px; color: #78716c; }}
  </style>
</head>
<body>
  <div class="card">
    <div class="header">
      <h1>PANNA BIRYANI</h1>
      <div class="badge">{severity} KITCHEN ALERT</div>
    </div>
    <div class="content">
      <div class="title">{title}</div>
      <div class="message">{message}</div>
"""
        ]

        if metadata:
            html_parts.append("""
      <table class="table">
        <thead>
          <tr>
            <th>Property</th>
            <th>Value</th>
          </tr>
        </thead>
        <tbody>
""")
            for k, v in metadata.items():
                label = k.replace("_", " ").title()
                html_parts.append(f"          <tr><td><strong>{label}</strong></td><td>{v}</td></tr>\n")
            html_parts.append("        </tbody>\n      </table>\n")

        html_parts.append(
            f"""
    </div>
    <div class="footer">
      Sent via Panna CRM Notification Engine &bull; {datetime.now(UTC).strftime('%d %b %Y, %I:%M %p UTC')}
    </div>
  </div>
</body>
</html>"""
        )

        return "".join(html_parts)

    def dispatch(
        self,
        title: str,
        message: str,
        severity: str,
        recipient: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        target_email = recipient or self.DEFAULT_ADMIN_EMAIL
        html_body = self.format_message(title, message, severity, metadata)
        plain_summary = f"{title}: {message}"
        mailto_url = f"mailto:{target_email}?subject={urllib.parse.quote(f'[{severity}] Panna Biryani Alert: {title}')}&body={urllib.parse.quote(plain_summary)}"

        return {
            "channel": "EMAIL",
            "recipient": target_email,
            "status": "MOCK_DELIVERED",
            "preview_content": html_body,
            "action_url": mailto_url,
            "dispatched_at": datetime.now(UTC),
        }
