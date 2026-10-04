import pytest
from fastapi.testclient import TestClient
from app.models.order import OrderStatus, PaymentStatus


def test_public_gateway_health(client: TestClient):
    """Test public website gateway health ping without auth."""
    res = client.get("/api/v1/public/orders/gateway/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "online"
    assert data["platform"] == "WEBSITE"


def test_submit_website_order_cod(client: TestClient):
    """Test customer placing an order from website with Cash on Delivery (no JWT needed)."""
    payload = {
        "customer": {
            "name": "Kavita Rao",
            "phone": "+91 9988776655",
            "email": "kavita.rao@example.com",
            "delivery_address": "Flat 302, Green Acres, Indiranagar, Bengaluru",
        },
        "items": [
            {
                "item_name": "Panna Royal Dum Biryani",
                "portion_size": "750g",
                "quantity": 1,
                "unit_price": 450.0,
                "notes": "Less spicy please",
            },
            {
                "item_name": "Gulab Jamun (2 pcs)",
                "portion_size": "Regular",
                "quantity": 2,
                "unit_price": 70.0,
            },
        ],
        "payment_method": "COD",
        "delivery_fee": 30.0,
        "discount": 0.0,
        "notes": "Ring bell twice upon delivery",
    }

    res = client.post("/api/v1/public/orders", json=payload)
    assert res.status_code == 201
    res_data = res.json()
    assert res_data["success"] is True
    order = res_data["data"]

    # Calculation: Subtotal = 450 + 2*70 = 590. Taxable = 590. Tax (5%) = 29.5. Total = 590 + 30 + 29.5 = 649.5
    assert order["order_number"].startswith("PB-W-")
    assert order["subtotal"] == 590.0
    assert order["delivery_fee"] == 30.0
    assert order["tax"] == 29.5
    assert order["total_amount"] == 649.5
    assert order["order_status"] == OrderStatus.NEW.value
    assert order["payment_status"] == PaymentStatus.PENDING.value
    assert order["tracking_token"].startswith("trk_")


def test_submit_website_order_prepaid_upi(client: TestClient):
    """Test customer placing an order from website with online UPI payment."""
    payload = {
        "customer": {
            "name": "Rohan Deshmukh",
            "phone": "+91 9876501234",
            "email": "rohan.d@example.com",
            "delivery_address": "House 12, 5th Cross, HSR Layout Sector 2",
        },
        "items": [
            {
                "item_name": "Panna Veg Dum Biryani",
                "portion_size": "1kg",
                "quantity": 1,
                "unit_price": 480.0,
            }
        ],
        "payment_method": "ONLINE_UPI",
        "delivery_fee": 0.0,
        "discount": 50.0,
    }

    res = client.post("/api/v1/public/orders", json=payload)
    assert res.status_code == 201
    order = res.json()["data"]

    # Calculation: Subtotal = 480. Discount = 50. Taxable = 430. Tax (5%) = 21.5. Total = 430 + 0 + 21.5 = 451.5
    assert order["subtotal"] == 480.0
    assert order["discount"] == 50.0
    assert order["tax"] == 21.5
    assert order["total_amount"] == 451.5
    assert order["order_status"] == OrderStatus.CONFIRMED.value
    assert order["payment_status"] == PaymentStatus.PAID.value


def test_track_website_order_lifecycle(client: TestClient):
    """Test public tracking endpoint returning timeline and sanitized customer info."""
    # 1. Place order
    payload = {
        "customer": {
            "name": "Aakash Varma",
            "phone": "+91 9123456780",
            "delivery_address": "Tower 4, Prestige Tech Park, Marathahalli",
        },
        "items": [
            {
                "item_name": "Panna Hyderabadi Dum Biryani",
                "portion_size": "500g",
                "quantity": 1,
                "unit_price": 350.0,
            }
        ],
        "payment_method": "COD",
    }
    create_res = client.post("/api/v1/public/orders", json=payload)
    assert create_res.status_code == 201
    order_number = create_res.json()["data"]["order_number"]

    # 2. Track order
    track_res = client.get(f"/api/v1/public/orders/track/{order_number}")
    assert track_res.status_code == 200
    track_data = track_res.json()["data"]

    assert track_data["order_number"] == order_number
    assert track_data["customer_name"] == "Aakash Varma"
    assert "****" in track_data["customer_phone_masked"]  # Privacy masked
    assert track_data["order_status"] == OrderStatus.NEW.value
    assert len(track_data["timeline"]) == 6
    assert track_data["timeline"][0]["step_key"] == "NEW"
    assert track_data["timeline"][0]["completed"] is True
    assert track_data["timeline"][0]["current"] is True


def test_payment_webhook_updates_status(client: TestClient):
    """Test payment webhook callback updating payment status and logging audit event."""
    # 1. Place COD order initially
    payload = {
        "customer": {
            "name": "Siddharth Jain",
            "phone": "+91 9777712345",
            "delivery_address": "Villa 18, Palm Meadows",
        },
        "items": [
            {
                "item_name": "Panna Paneer Dum Biryani",
                "portion_size": "500g",
                "quantity": 1,
                "unit_price": 320.0,
            }
        ],
        "payment_method": "COD",
    }
    create_res = client.post("/api/v1/public/orders", json=payload)
    order_num = create_res.json()["data"]["order_number"]

    # 2. Trigger webhook to confirm online payment post-checkout
    webhook_payload = {
        "payment_status": "PAID",
        "transaction_id": "pay_live_rzp_987654321",
        "payment_gateway": "RAZORPAY",
        "notes": "UPI payment verified via webhook",
    }
    wh_res = client.post(f"/api/v1/public/orders/{order_num}/payment-webhook", json=webhook_payload)
    assert wh_res.status_code == 200
    data = wh_res.json()["data"]
    assert data["success"] is True
    assert data["new_payment_status"] == "PAID"
    assert data["order_status"] == OrderStatus.CONFIRMED.value


def test_submit_website_order_invalid_payload(client: TestClient):
    """Verify validation rejection on empty items or invalid phone number."""
    payload = {
        "customer": {
            "name": "Invalid Customer",
            "phone": "123",  # Too short
            "delivery_address": "12",  # Too short
        },
        "items": [],  # Empty items
        "payment_method": "COD",
    }
    res = client.post("/api/v1/public/orders", json=payload)
    assert res.status_code == 422
