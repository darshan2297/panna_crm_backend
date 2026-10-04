import pytest


def get_token_for(client, username="admin", password="admin123"):
    resp = client.post(
        "/api/v1/auth/login",
        json={"username_or_email": username, "password": password},
    )
    assert resp.status_code == 200, f"Login failed: {resp.text}"
    return resp.json()["access_token"]


def seed_test_items(client, token):
    inv_res = client.post(
        "/api/v1/inventory/items",
        json={
            "name": "Phase 9 Basmati Rice",
            "sku": "ING-P9-RICE",
            "category": "GRAIN",
            "unit": "kg",
            "current_stock": 5.0,
            "minimum_stock": 10.0,
            "reorder_level": 25.0,
            "purchase_price": 140.0,
            "supplier": "Royal Agro Traders",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    inv_id = inv_res.json()["data"]["id"]

    pkg_res = client.post(
        "/api/v1/packaging/items",
        json={
            "name": "Phase 9 Biryani Box 500ml",
            "sku": "PKG-P9-BOX500",
            "category": "CONTAINER",
            "material": "Food Grade PP",
            "capacity": "500ml",
            "unit": "pcs",
            "current_stock": 40.0,
            "minimum_stock": 80.0,
            "reorder_level": 150.0,
            "purchase_cost": 6.50,
            "supplier": "EcoPackaging India",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    pkg_id = pkg_res.json()["data"]["id"]
    return inv_id, pkg_id


def test_scan_and_list_notifications(client):
    token = get_token_for(client)
    seed_test_items(client, token)

    # 1. Trigger stock scan
    scan_resp = client.post(
        "/api/v1/notifications/scan",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert scan_resp.status_code == 200
    assert scan_resp.json()["success"] is True

    # 2. List notifications
    list_resp = client.get(
        "/api/v1/notifications",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert list_resp.status_code == 200
    data = list_resp.json()["data"]
    assert "total" in data
    assert "items" in data
    assert len(data["items"]) > 0

    first_notif = data["items"][0]
    assert "title" in first_notif
    assert "message" in first_notif
    assert "type" in first_notif
    assert "severity" in first_notif


def test_notification_unread_and_mark_read(client):
    token = get_token_for(client)
    seed_test_items(client, token)
    client.post("/api/v1/notifications/scan", headers={"Authorization": f"Bearer {token}"})

    # Get unread count
    count_resp = client.get(
        "/api/v1/notifications/unread-count",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert count_resp.status_code == 200
    unread_data = count_resp.json()["data"]
    assert "unread_count" in unread_data

    # List items to get an unread ID
    list_resp = client.get(
        "/api/v1/notifications?is_read=false",
        headers={"Authorization": f"Bearer {token}"},
    )
    items = list_resp.json()["data"]["items"]
    if items:
        notif_id = items[0]["id"]
        # Mark single as read
        read_resp = client.patch(
            f"/api/v1/notifications/{notif_id}/read",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert read_resp.status_code == 200
        assert read_resp.json()["data"]["is_read"] is True

    # Mark all as read
    mark_all_resp = client.post(
        "/api/v1/notifications/mark-all-read",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert mark_all_resp.status_code == 200

    # Unread count should now be 0
    count_resp2 = client.get(
        "/api/v1/notifications/unread-count",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert count_resp2.json()["data"]["unread_count"] == 0


def test_notification_summary(client):
    token = get_token_for(client)
    seed_test_items(client, token)
    client.post("/api/v1/notifications/scan", headers={"Authorization": f"Bearer {token}"})

    resp = client.get(
        "/api/v1/notifications/summary",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    summary = resp.json()["data"]
    assert "total_notifications" in summary
    assert "unread_count" in summary
    assert "critical_count" in summary
    assert "warning_count" in summary
    assert "stock_alert_count" in summary


def test_notification_dispatch_adapters(client):
    token = get_token_for(client)
    seed_test_items(client, token)
    client.post("/api/v1/notifications/scan", headers={"Authorization": f"Bearer {token}"})

    # Get any notification
    list_resp = client.get(
        "/api/v1/notifications?page_size=1",
        headers={"Authorization": f"Bearer {token}"},
    )
    items = list_resp.json()["data"]["items"]
    assert len(items) > 0, "Expected at least 1 notification"
    notif_id = items[0]["id"]

    # 1. Dispatch via WhatsApp
    wa_resp = client.post(
        f"/api/v1/notifications/{notif_id}/dispatch",
        json={
            "channel": "WHATSAPP",
            "recipient": "+919876543210",
            "custom_message": "Immediate reorder required for kitchen operations.",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert wa_resp.status_code == 200
    wa_data = wa_resp.json()["data"]
    assert wa_data["channel"] == "WHATSAPP"
    assert wa_data["status"] == "MOCK_DELIVERED"
    assert "wa.me" in wa_data["action_url"]
    assert "PANNA BIRYANI" in wa_data["preview_content"]

    # 2. Dispatch via Email
    email_resp = client.post(
        f"/api/v1/notifications/{notif_id}/dispatch",
        json={
            "channel": "EMAIL",
            "recipient": "kitchen-head@pannabiryani.com",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert email_resp.status_code == 200
    email_data = email_resp.json()["data"]
    assert email_data["channel"] == "EMAIL"
    assert email_data["status"] == "MOCK_DELIVERED"
    assert "mailto:" in email_data["action_url"]
    assert "PANNA BIRYANI" in email_data["preview_content"]


def test_restock_deficit_suggestions_and_summary(client):
    token = get_token_for(client)
    seed_test_items(client, token)

    # Suggestions endpoint
    sug_resp = client.get(
        "/api/v1/restock/suggestions",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert sug_resp.status_code == 200
    sug_items = sug_resp.json()["data"]
    assert isinstance(sug_items, list)
    assert len(sug_items) > 0

    first_sug = sug_items[0]
    assert "name" in first_sug
    assert "sku" in first_sug
    assert "suggested_order_qty" in first_sug
    assert "estimated_cost" in first_sug
    assert "status" in first_sug

    # Summary endpoint
    sum_resp = client.get(
        "/api/v1/restock/summary",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert sum_resp.status_code == 200
    sum_data = sum_resp.json()["data"]
    assert "total_deficit_items" in sum_data
    assert "estimated_restock_investment_inr" in sum_data
    assert sum_data["total_deficit_items"] > 0


def test_create_and_receive_restock_order(client):
    token = get_token_for(client)
    inv_id, pkg_id = seed_test_items(client, token)

    # Create new PO using real seeded IDs
    create_payload = {
        "supplier_name": "Metro Cash & Carry Wholesale",
        "supplier_contact": "+91 98111 22334",
        "target_type": "MIXED",
        "notes": "Emergency restock batch for Biryani Handis and Farm Chicken.",
        "created_by_name": "Test Manager",
        "items": [
            {
                "item_type": "INVENTORY",
                "item_id": inv_id,
                "ordered_quantity": 25.0,
                "unit_cost": 140.0,
            },
            {
                "item_type": "PACKAGING",
                "item_id": pkg_id,
                "ordered_quantity": 200.0,
                "unit_cost": 6.50,
            },
        ],
    }

    create_resp = client.post(
        "/api/v1/restock/orders",
        json=create_payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert create_resp.status_code == 200
    order = create_resp.json()["data"]
    po_id = order["id"]
    assert order["status"] == "DRAFT"
    assert order["supplier_name"] == "Metro Cash & Carry Wholesale"
    assert len(order["items"]) == 2
    assert order["total_estimated_cost"] == 25.0 * 140.0 + 200.0 * 6.50

    # Advance status to ORDERED
    status_resp = client.patch(
        f"/api/v1/restock/orders/{po_id}/status",
        json={"status": "ORDERED"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert status_resp.status_code == 200
    assert status_resp.json()["data"]["status"] == "ORDERED"

    # Get initial stock of inventory item
    inv_resp = client.get(
        f"/api/v1/inventory/items/{inv_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    initial_stock = inv_resp.json()["data"]["current_stock"]

    # 1-Click Receive PO Goods
    receive_resp = client.post(
        f"/api/v1/restock/orders/{po_id}/receive",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert receive_resp.status_code == 200
    received_order = receive_resp.json()["data"]
    assert received_order["status"] == "RECEIVED"
    assert received_order["received_at"] is not None
    assert all(item["is_received"] is True for item in received_order["items"])

    # Verify inventory stock was automatically incremented
    inv_resp_after = client.get(
        f"/api/v1/inventory/items/{inv_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    new_stock = inv_resp_after.json()["data"]["current_stock"]
    assert new_stock == round(initial_stock + 25.0, 2)
