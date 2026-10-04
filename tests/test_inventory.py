import pytest


def get_token_for(client, username="admin", password="admin123"):
    resp = client.post(
        "/api/v1/auth/login",
        json={"username_or_email": username, "password": password},
    )
    assert resp.status_code == 200, f"Login failed: {resp.text}"
    return resp.json()["access_token"]


def test_inventory_summary(client):
    token = get_token_for(client)

    # Ensure at least one item exists
    client.post(
        "/api/v1/inventory/items",
        json={
            "name": "Summary Test Basmati Rice",
            "sku": "ING-TEST-RIC01",
            "category": "GRAIN",
            "unit": "kg",
            "current_stock": 20.0,
            "minimum_stock": 5.0,
            "reorder_level": 10.0,
            "purchase_price": 120.0,
        },
        headers={"Authorization": f"Bearer {token}"},
    )

    resp = client.get(
        "/api/v1/inventory/summary",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    summary = data["data"]
    assert "total_items" in summary
    assert "in_stock_items" in summary
    assert "low_stock_items" in summary
    assert "total_inventory_value_inr" in summary
    assert "category_valuations" in summary
    assert summary["total_items"] > 0
    assert summary["total_inventory_value_inr"] > 0


def test_create_and_list_inventory_items(client):
    token = get_token_for(client)

    # 1. Create ingredient
    payload = {
        "name": "Royal Shahi Jeera (Caraway Seeds)",
        "sku": "ING-SPICE-SJ01",
        "category": "SPICE",
        "unit": "kg",
        "current_stock": 5.0,
        "minimum_stock": 2.0,
        "reorder_level": 4.0,
        "purchase_price": 450.0,
        "supplier": "Old Delhi Spice Merchants",
        "storage_location": "Dry Pantry Rack 4",
        "description": "Premium whole caraway seeds for rice tempering",
        "is_active": True,
    }
    create_resp = client.post(
        "/api/v1/inventory/items",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert create_resp.status_code == 201
    item_data = create_resp.json()["data"]
    assert item_data["name"] == "Royal Shahi Jeera (Caraway Seeds)"
    assert item_data["sku"] == "ING-SPICE-SJ01"
    assert item_data["total_valuation"] == 2250.0
    assert item_data["is_low_stock"] is False
    item_id = item_data["id"]

    # 2. List with filter
    list_resp = client.get(
        "/api/v1/inventory/items?category=SPICE&search=Shahi+Jeera",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert list_resp.status_code == 200
    items = list_resp.json()["data"]["items"]
    assert any(i["id"] == item_id for i in items)

    # 3. Get item details
    detail_resp = client.get(
        f"/api/v1/inventory/items/{item_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert detail_resp.status_code == 200
    assert detail_resp.json()["data"]["name"] == "Royal Shahi Jeera (Caraway Seeds)"


def test_item_stock_adjustments_and_transactions(client):
    token = get_token_for(client)

    # 1. Create test item
    payload = {
        "name": "Kashmiri Degi Mirch Powder",
        "sku": "ING-SPICE-DM01",
        "category": "SPICE",
        "unit": "kg",
        "current_stock": 10.0,
        "minimum_stock": 3.0,
        "reorder_level": 6.0,
        "purchase_price": 320.0,
        "supplier": "Kashmir Spices",
    }
    create_resp = client.post(
        "/api/v1/inventory/items",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert create_resp.status_code == 201
    item_id = create_resp.json()["data"]["id"]

    # 2. Stock In (Purchase delivery)
    in_resp = client.post(
        f"/api/v1/inventory/items/{item_id}/adjust",
        json={
            "transaction_type": "STOCK_IN",
            "quantity": 15.0,
            "unit_price": 320.0,
            "reference_no": "PO-TEST-001",
            "notes": "Received fresh batch delivery",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert in_resp.status_code == 200
    in_data = in_resp.json()["data"]
    assert in_data["stock_before"] == 10.0
    assert in_data["stock_after"] == 25.0
    assert in_data["total_cost"] == 4800.0

    # 3. Stock Out (Kitchen consumption)
    out_resp = client.post(
        f"/api/v1/inventory/items/{item_id}/adjust",
        json={
            "transaction_type": "STOCK_OUT",
            "quantity": 8.0,
            "reference_no": "KITCHEN-BATCH-01",
            "notes": "Issued for daily curry base marination",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert out_resp.status_code == 200
    assert out_resp.json()["data"]["stock_before"] == 25.0
    assert out_resp.json()["data"]["stock_after"] == 17.0

    # 4. Wastage (Accidental spill / quality rejection)
    waste_resp = client.post(
        f"/api/v1/inventory/items/{item_id}/adjust",
        json={
            "transaction_type": "WASTAGE",
            "quantity": 1.5,
            "reference_no": "WASTE-01",
            "notes": "Moisture damage in open packet",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert waste_resp.status_code == 200
    assert waste_resp.json()["data"]["stock_after"] == 15.5

    # 5. Over-deduction prevention check
    fail_resp = client.post(
        f"/api/v1/inventory/items/{item_id}/adjust",
        json={
            "transaction_type": "STOCK_OUT",
            "quantity": 999.0,
            "notes": "Attempt impossible reduction",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert fail_resp.status_code == 400
    assert "Insufficient stock" in fail_resp.json()["detail"]

    # 6. Audit correction (Physical stock count)
    audit_resp = client.post(
        f"/api/v1/inventory/items/{item_id}/adjust",
        json={
            "transaction_type": "AUDIT_CORRECTION",
            "quantity": 16.0,
            "reference_no": "WEEKLY-AUDIT",
            "notes": "Physical inventory count reconciliation",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert audit_resp.status_code == 200
    assert audit_resp.json()["data"]["stock_after"] == 16.0

    # 7. Check transaction history
    tx_list_resp = client.get(
        f"/api/v1/inventory/transactions?item_id={item_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert tx_list_resp.status_code == 200
    txs = tx_list_resp.json()["data"]["items"]
    assert len(txs) >= 4


def test_low_stock_and_critical_stock_filtering(client):
    token = get_token_for(client)

    # Create an item that is critically low on stock
    crit_payload = {
        "name": "Kewra Water Essence",
        "sku": "ING-FLAV-KW01",
        "category": "OTHER",
        "unit": "l",
        "current_stock": 1.0,
        "minimum_stock": 2.0,
        "reorder_level": 5.0,
        "purchase_price": 90.0,
    }
    client.post(
        "/api/v1/inventory/items",
        json=crit_payload,
        headers={"Authorization": f"Bearer {token}"},
    )

    resp = client.get(
        "/api/v1/inventory/items?status_filter=CRITICAL_STOCK",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    items = resp.json()["data"]["items"]
    crit_item = next((i for i in items if i["sku"] == "ING-FLAV-KW01"), None)
    assert crit_item is not None
    assert crit_item["is_critical_stock"] is True
    assert crit_item["is_low_stock"] is True


def test_staff_adjusts_stock_and_admin_deletes(client):
    admin_token = get_token_for(client, "admin", "admin123")
    staff_token = get_token_for(client, "staff", "staff123")

    # Create item with Admin
    create_resp = client.post(
        "/api/v1/inventory/items",
        json={
            "name": "Star Anise Whole (Chakra Phool)",
            "sku": "ING-SPICE-SA01",
            "category": "SPICE",
            "unit": "kg",
            "current_stock": 8.0,
            "minimum_stock": 2.0,
            "reorder_level": 4.0,
            "purchase_price": 600.0,
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert create_resp.status_code == 201
    item_id = create_resp.json()["data"]["id"]

    # Staff performs stock adjustment
    staff_adj_resp = client.post(
        f"/api/v1/inventory/items/{item_id}/adjust",
        json={
            "transaction_type": "STOCK_OUT",
            "quantity": 1.0,
            "notes": "Staff kitchen usage",
        },
        headers={"Authorization": f"Bearer {staff_token}"},
    )
    assert staff_adj_resp.status_code == 200
    assert staff_adj_resp.json()["data"]["stock_after"] == 7.0

    # Staff attempts deletion -> should be 403 Forbidden
    staff_del_resp = client.delete(
        f"/api/v1/inventory/items/{item_id}",
        headers={"Authorization": f"Bearer {staff_token}"},
    )
    assert staff_del_resp.status_code == 403

    # Admin deletes -> should be 200 OK
    admin_del_resp = client.delete(
        f"/api/v1/inventory/items/{item_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert admin_del_resp.status_code == 200
