"""
Razorpay payment service.

All Razorpay API calls happen here, in the CRM backend, where the
Key ID / Key Secret live. The storefront never touches the secret.

Uses basic auth (key_id as username, key_secret as password) against
the Razorpay REST API — no extra SDK dependency required.
"""

import hashlib
import hmac
import logging
from typing import Any

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

RAZORPAY_API = "https://api.razorpay.com/v1"


class PaymentService:
    """Thin wrapper around the Razorpay REST API with HMAC verification."""

    def __init__(self) -> None:
        self.key_id = (settings.RAZORPAY_KEY_ID or "").strip()
        self.key_secret = (settings.RAZORPAY_SECRET_KEY or "").strip()

    @property
    def enabled(self) -> bool:
        """True only when real credentials are configured."""
        return bool(self.key_id and self.key_secret)

    # ------------------------------------------------------------------ #
    # Create order
    # ------------------------------------------------------------------ #
    def create_order(
        self,
        order_number: str,
        amount: float,
        customer_name: str = "",
        customer_phone: str = "",
    ) -> dict[str, Any] | None:
        """Create a Razorpay order. Returns {razorpay_order_id, amount, key_id, currency}.

        Returns None when the gateway is disabled (no keys configured) so the
        caller can fall back to a mock/COD flow.
        """
        if not self.enabled:
            return None

        payload = {
            "amount": int(round(amount * 100)),  # Razorpay expects paise
            "currency": "INR",
            "receipt": order_number,
            "notes": {
                "order_number": order_number,
                "customer": customer_name,
                "phone": customer_phone,
            },
        }

        try:
            resp = httpx.post(
                f"{RAZORPAY_API}/orders",
                auth=(self.key_id, self.key_secret),
                json=payload,
                timeout=20.0,
            )
            resp.raise_for_status()
        except httpx.HTTPStatusError as exc:
            logger.error(
                "Razorpay create_order failed for %s: %s %s",
                order_number,
                exc.response.status_code,
                exc.response.text[:500],
            )
            raise
        except httpx.HTTPError as exc:
            logger.error("Razorpay create_order network error for %s: %s", order_number, exc)
            raise

        data = resp.json()
        return {
            "razorpay_order_id": data["id"],
            "amount": data["amount"],
            "currency": data["currency"],
            "key_id": self.key_id,
        }

    # ------------------------------------------------------------------ #
    # Verify payment signature (checkout callback)
    # ------------------------------------------------------------------ #
    def verify_payment_signature(
        self,
        razorpay_order_id: str,
        razorpay_payment_id: str,
        razorpay_signature: str,
    ) -> bool:
        """Verify the signature Razorpay returns after checkout.

        Razorpay computes HMAC_SHA256(key_secret, `${order_id}|${payment_id}`).
        """
        if not self.enabled:
            # No keys configured -> mock mode, accept any non-empty signature.
            return bool(razorpay_signature)

        expected = f"{razorpay_order_id}|{razorpay_payment_id}".encode()
        computed = hmac.new(
            self.key_secret.encode(), expected, hashlib.sha256
        ).hexdigest()
        return hmac.compare_digest(computed, razorpay_signature or "")

    # ------------------------------------------------------------------ #
    # Verify webhook signature (Razorpay -> our /webhook endpoint)
    # ------------------------------------------------------------------ #
    def verify_webhook_signature(self, raw_body: bytes, signature: str) -> bool:
        """Verify the X-Razorpay-Signature header of an incoming webhook.

        Razorpay sends `sha256=<hex>` where the HMAC is computed over the raw
        request body using the webhook secret (here we use the key secret).
        """
        if not self.enabled:
            return True

        computed = hmac.new(self.key_secret.encode(), raw_body, hashlib.sha256).hexdigest()
        # Header format: "sha256=<hex>"
        provided = signature.strip()
        if "=" in provided:
            provided = provided.split("=", 1)[1]
        return hmac.compare_digest(computed, provided)

    # ------------------------------------------------------------------ #
    # Fetch payment (optional sanity check)
    # ------------------------------------------------------------------ #
    def fetch_payment(self, razorpay_payment_id: str) -> dict[str, Any] | None:
        """Fetch a payment from Razorpay to confirm its amount/status."""
        if not self.enabled:
            return None
        try:
            resp = httpx.get(
                f"{RAZORPAY_API}/payments/{razorpay_payment_id}",
                auth=(self.key_id, self.key_secret),
                timeout=20.0,
            )
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPError as exc:
            logger.error("Razorpay fetch_payment error for %s: %s", razorpay_payment_id, exc)
            return None

    # ------------------------------------------------------------------ #
    # Refund a captured payment
    # ------------------------------------------------------------------ #
    def refund_payment(
        self,
        razorpay_payment_id: str,
        amount: float | None = None,
        speed: str = "normal",
    ) -> dict[str, Any]:
        """Refund a captured Razorpay payment (full refund when amount is None)."""
        if not self.enabled:
            raise RuntimeError("Razorpay is not configured; cannot issue refund.")

        payload: dict[str, Any] = {"payment_id": razorpay_payment_id, "speed": speed}
        if amount is not None:
            payload["amount"] = int(round(amount * 100))  # paise

        resp = httpx.post(
            f"{RAZORPAY_API}/refunds",
            auth=(self.key_id, self.key_secret),
            json=payload,
            timeout=20.0,
        )
        resp.raise_for_status()
        return resp.json()


payment_service = PaymentService()
