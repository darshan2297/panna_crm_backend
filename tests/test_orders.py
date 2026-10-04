import pytest
from fastapi.testclient import TestClient
from app.models.order import OrderPlatform, OrderStatus, PaymentStatus


def get_auth_token(client: TestClient, username: str = "admin", password: str = "admin123") -> str:
    res = client.post("/api/v1/auth/login", json={"username_or_email": username, "password": password})
    assert res.status_code == 200
    return res.json()["access_token"]


def test_create_order_website(client: TestClient):
    token = get_auth_token(client)
    headers = {"Authorization": f"Bearer {token}"}

    payload = {
        "platform": OrderPlatform.WEBSITE.value,
        "customer_name": "Tanya Singhania",
        "customer_phone": "+91 9888877771",
        "customer_email": "tanya@example.com",
        "delivery_address": "402 Palm Heights, Koramangala 4th Block",
        "items": [
            {
                "item_name": "Panna Paneer Dum Biryani",
                "portion_size": "500g",
                "quantity": 2,
                "unit_price": 320.0,
            },
            {
                "item_name": "Panna Special Raita",
                "portion_size": "250g",
                "quantity": 1,
                "unit_price": 60.0,
            },
        ],
        "discount": 50.0,
        "delivery_fee": 40.0,
        "payment_status": PaymentStatus.PAID.value,
        "notes": "Extra spicy biryani, deliver before 8 PM",
    }

    res = client.post("/api/v1/orders", json=payload, headers=headers)
    assert res.status_code == 201
    data = res.json()["data"]

    # Verify calculation: Subtotal = 2*320 + 60 = 700. Discount = 50. Taxable = 650. Tax (5%) = 32.5. Total = 650 + 40 + 32.5 = 722.5
    assert data["customer_name"] == "Tanya Singhania"
    assert data["customer_phone"] == "+91 9888877771"
    assert data["subtotal"] == 700.0
    assert data["discount"] == 50.0
    assert data["delivery_fee"] == 40.0
    assert data["tax"] == 32.5
    assert data["total_amount"] == 722.5
    assert data["order_status"] == OrderStatus.NEW.value
    assert data["payment_status"] == PaymentStatus.PAID.value
    assert len(data["items"]) == 2
    assert len(data["status_history"]) == 1
    assert data["customer"]["name"] == "Tanya Singhania"
    assert data["customer"]["total_orders"] == 1


def test_list_orders_and_filters(client: TestClient):
    token = get_auth_token(client)
    headers = {"Authorization": f"Bearer {token}"}

    # Create test orders
    client.post(
        "/api/v1/orders",
        json={
            "platform": OrderPlatform.WEBSITE.value,
            "customer_name": "Tanya Singhania",
            "customer_phone": "+91 9888877771",
            "items": [{"item_name": "Dum Biryani", "portion_size": "500g", "quantity": 1, "unit_price": 300.0}],
        },
        headers=headers,
    )
    client.post(
        "/api/v1/orders",
        json={
            "platform": OrderPlatform.ZOMATO.value,
            "customer_name": "Karan Johar",
            "customer_phone": "+91 9777700000",
            "items": [{"item_name": "Paneer Biryani", "portion_size": "500g", "quantity": 1, "unit_price": 320.0}],
        },
        headers=headers,
    )

    # Query all
    res = client.get("/api/v1/orders", headers=headers)
    assert res.status_code == 200
    res_data = res.json()
    assert "items" in res_data
    assert "total" in res_data
    assert res_data["total"] >= 2

    # Filter by platform
    res_plat = client.get(f"/api/v1/orders?platform={OrderPlatform.WEBSITE.value}", headers=headers)
    assert res_plat.status_code == 200
    for order in res_plat.json()["items"]:
        assert order["platform"] == OrderPlatform.WEBSITE.value

    # Search by customer phone or name
    res_search = client.get("/api/v1/orders?search=Singhania", headers=headers)
    assert res_search.status_code == 200
    assert len(res_search.json()["items"]) >= 1
    assert "Singhania" in res_search.json()["items"][0]["customer_name"]


def test_order_status_progression_and_history(client: TestClient):
    token = get_auth_token(client)
    headers = {"Authorization": f"Bearer {token}"}

    # Create an order
    order_res = client.post(
        "/api/v1/orders",
        json={
            "platform": OrderPlatform.ZOMATO.value,
            "customer_name": "Arjun Kapoor",
            "customer_phone": "+91 9123456780",
            "items": [
                {
                    "item_name": "Panna Hyderabadi Dum Biryani",
                    "portion_size": "1kg",
                    "quantity": 1,
                    "unit_price": 550.0,
                }
            ],
        },
        headers=headers,
    )
    order_id = order_res.json()["data"]["id"]

    # Progression: NEW -> CONFIRMED
    res1 = client.patch(
        f"/api/v1/orders/{order_id}/status",
        json={"new_status": OrderStatus.CONFIRMED.value, "notes": "Kitchen accepted Zomato ticket"},
        headers=headers,
    )
    assert res1.status_code == 200
    assert res1.json()["data"]["order_status"] == OrderStatus.CONFIRMED.value

    # Progression: CONFIRMED -> PREPARING
    res2 = client.patch(
        f"/api/v1/orders/{order_id}/status",
        json={"new_status": OrderStatus.PREPARING.value, "notes": "Biryani handi on dum"},
        headers=headers,
    )
    assert res2.status_code == 200
    assert res2.json()["data"]["order_status"] == OrderStatus.PREPARING.value

    # Progression: PREPARING -> READY
    res3 = client.patch(
        f"/api/v1/orders/{order_id}/status",
        json={"new_status": OrderStatus.READY.value, "notes": "Packed in thermal bag"},
        headers=headers,
    )
    assert res3.status_code == 200
    assert res3.json()["data"]["order_status"] == OrderStatus.READY.value

    # Inspect order details and verify history trail
    detail_res = client.get(f"/api/v1/orders/{order_id}", headers=headers)
    assert detail_res.status_code == 200
    data = detail_res.json()["data"]
    assert len(data["status_history"]) == 4  # Initial NEW + CONFIRMED + PREPARING + READY
    assert data["platform"] == OrderPlatform.ZOMATO.value
    assert data["estimated_commission"] > 0  # 22% Zomato commission estimated


def test_cancel_order(client: TestClient):
    token = get_auth_token(client)
    headers = {"Authorization": f"Bearer {token}"}

    # Create an order
    order_res = client.post(
        "/api/v1/orders",
        json={
            "platform": OrderPlatform.SWIGGY.value,
            "customer_name": "Rohan Deshmukh",
            "customer_phone": "+91 9777766665",
            "items": [
                {
                    "item_name": "Panna Veg Dum Biryani",
                    "portion_size": "500g",
                    "quantity": 1,
                    "unit_price": 260.0,
                }
            ],
        },
        headers=headers,
    )
    order_id = order_res.json()["data"]["id"]

    # Cancel order
    cancel_res = client.post(
        f"/api/v1/orders/{order_id}/cancel",
        json={"reason": "Customer called to cancel delivery due to change of plans"},
        headers=headers,
    )
    assert cancel_res.status_code == 200
    data = cancel_res.json()["data"]
    assert data["order_status"] == OrderStatus.CANCELLED.value

    # Verify history includes reason
    history_entries = data["status_history"]
    assert any("Customer called to cancel" in (h.get("notes") or "") for h in history_entries)


def test_order_status_summary(client: TestClient):
    token = get_auth_token(client)
    headers = {"Authorization": f"Bearer {token}"}

    client.post(
        "/api/v1/orders",
        json={
            "platform": OrderPlatform.WEBSITE.value,
            "customer_name": "Summary Test Customer",
            "customer_phone": "+91 9555544443",
            "items": [{"item_name": "Veg Biryani", "portion_size": "500g", "quantity": 1, "unit_price": 260.0}],
        },
        headers=headers,
    )

    res = client.get("/api/v1/orders/summary", headers=headers)
    assert res.status_code == 200
    data = res.json()["data"]
    assert "total_orders" in data
    assert "new" in data
    assert "preparing" in data
    assert "ready" in data
    assert "cancelled" in data
    assert data["total_orders"] >= 1

