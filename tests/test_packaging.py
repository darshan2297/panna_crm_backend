import pytest


def get_token_for(client, username="admin", password="admin123"):
    resp = client.post(
        "/api/v1/auth/login",
        json={"username_or_email": username, "password": password},
    )
    assert resp.status_code == 200, f"Login failed: {resp.text}"
    return resp.json()["access_token"]


def test_packaging_summary(client):
    token = get_token_for(client)

    # Ensure at least one item exists
    client.post(
        "/api/v1/packaging/items",
        json={
            "name": "Summary Test Biryani Container",
            "sku": "PKG-SUM-001",
            "category": "CONTAINER",
            "material": "Food Grade PP",
            "capacity": "500ml",
            "unit": "pcs",
            "current_stock": 100.0,
            "minimum_stock": 20.0,
            "reorder_level": 40.0,
            "purchase_cost": 6.50,
        },
        headers={"Authorization": f"Bearer {token}"},
    )

    resp = client.get(
        "/api/v1/packaging/summary",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    summary = data["data"]
    assert "total_items" in summary
    assert "in_stock_items" in summary
    assert "low_stock_items" in summary
    assert "critical_stock_items" in summary
    assert "total_packaging_value_inr" in summary
    assert "category_valuations" in summary
    assert summary["total_items"] > 0
    assert summary["total_packaging_value_inr"] > 0


def test_create_and_list_packaging_items(client):
    token = get_token_for(client)

    # 1. Create packaging item
    payload = {
        "name": "Test 750ml Biryani Handi Box",
        "sku": "PKG-TST-BOX750",
        "category": "CONTAINER",
        "material": "Food Grade PP",
        "capacity": "750ml",
        "unit": "pcs",
        "current_stock": 150.0,
        "minimum_stock": 50.0,
        "reorder_level": 80.0,
        "purchase_cost": 8.50,
        "supplier": "Test Packaging Vendor",
        "storage_location": "Aisle T-1",
        "description": "Test 750ml container description",
    }
    create_resp = client.post(
        "/api/v1/packaging/items",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert create_resp.status_code == 201
    item_data = create_resp.json()["data"]
    item_id = item_data["id"]
    assert item_data["name"] == payload["name"]
    assert item_data["current_stock"] == 150.0
    assert item_data["total_valuation"] == 150.0 * 8.50

    # 2. List with category filter
    list_resp = client.get(
        "/api/v1/packaging/items?category=CONTAINER",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert list_resp.status_code == 200
    paginated = list_resp.json()["data"]
    assert any(it["id"] == item_id for it in paginated["items"])

    # 3. List with search query
    search_resp = client.get(
        "/api/v1/packaging/items?search=BOX750",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert search_resp.status_code == 200
    search_items = search_resp.json()["data"]["items"]
    assert len(search_items) >= 1
    assert search_items[0]["id"] == item_id


def test_packaging_item_detail_and_update(client):
    token = get_token_for(client)

    # Create item
    payload = {
        "name": "Test Update Salan Pouch",
        "category": "ACCOMPANIMENT",
        "material": "Multi-layer Foil",
        "capacity": "60ml",
        "unit": "pcs",
        "current_stock": 200.0,
        "minimum_stock": 60.0,
        "reorder_level": 100.0,
        "purchase_cost": 2.00,
    }
    create_resp = client.post(
        "/api/v1/packaging/items",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert create_resp.status_code == 201
    item_id = create_resp.json()["data"]["id"]

    # Retrieve details
    detail_resp = client.get(
        f"/api/v1/packaging/items/{item_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert detail_resp.status_code == 200
    assert detail_resp.json()["data"]["id"] == item_id
    assert "recent_transactions" in detail_resp.json()["data"]

    # Update item
    update_resp = client.patch(
        f"/api/v1/packaging/items/{item_id}",
        json={"purchase_cost": 2.50, "current_stock": 250.0},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert update_resp.status_code == 200
    updated_data = update_resp.json()["data"]
    assert updated_data["purchase_cost"] == 2.50
    assert updated_data["current_stock"] == 250.0
    assert updated_data["total_valuation"] == 250.0 * 2.50


def test_packaging_stock_adjustments(client):
    token = get_token_for(client)

    # Create test item
    payload = {
        "name": "Test Stock Adjustment Raita Bowl",
        "category": "ACCOMPANIMENT",
        "material": "Food Grade PP",
        "unit": "pcs",
        "current_stock": 100.0,
        "minimum_stock": 30.0,
        "reorder_level": 50.0,
        "purchase_cost": 1.50,
    }
    create_resp = client.post(
        "/api/v1/packaging/items",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    item_id = create_resp.json()["data"]["id"]

    # 1. STOCK_IN (+50)
    in_resp = client.post(
        f"/api/v1/packaging/items/{item_id}/adjust",
        json={
            "transaction_type": "STOCK_IN",
            "quantity": 50.0,
            "unit_cost": 1.50,
            "reference_no": "PO-TEST-101",
            "notes": "Bulk restock received from supplier",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert in_resp.status_code == 200
    assert in_resp.json()["data"]["current_stock"] == 150.0

    # 2. STOCK_OUT (-20)
    out_resp = client.post(
        f"/api/v1/packaging/items/{item_id}/adjust",
        json={
            "transaction_type": "STOCK_OUT",
            "quantity": 20.0,
            "notes": "Kitchen packing consumption batch 1",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert out_resp.status_code == 200
    assert out_resp.json()["data"]["current_stock"] == 130.0

    # 3. WASTAGE (-5 damaged in transit)
    waste_resp = client.post(
        f"/api/v1/packaging/items/{item_id}/adjust",
        json={
            "transaction_type": "WASTAGE",
            "quantity": 5.0,
            "notes": "Damaged snap lids discarded",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert waste_resp.status_code == 200
    assert waste_resp.json()["data"]["current_stock"] == 125.0

    # 4. Insufficient stock check (trying to deduct 500 when only 125 available)
    excess_resp = client.post(
        f"/api/v1/packaging/items/{item_id}/adjust",
        json={
            "transaction_type": "STOCK_OUT",
            "quantity": 500.0,
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert excess_resp.status_code == 400
    assert "Insufficient stock" in excess_resp.json()["detail"]


def test_packaging_transactions_audit_log(client):
    token = get_token_for(client)

    # Create item with opening stock to produce a transaction
    item_resp = client.post(
        "/api/v1/packaging/items",
        json={
            "name": "Audit Log Test Kraft Bag",
            "category": "BAG",
            "material": "Kraft Paper",
            "unit": "pcs",
            "current_stock": 200.0,
            "minimum_stock": 50.0,
            "reorder_level": 100.0,
            "purchase_cost": 5.0,
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    item_id = item_resp.json()["data"]["id"]

    # Record a stock adjustment
    client.post(
        f"/api/v1/packaging/items/{item_id}/adjust",
        json={
            "transaction_type": "STOCK_OUT",
            "quantity": 25.0,
            "notes": "Evening dispatch consumption",
        },
        headers={"Authorization": f"Bearer {token}"},
    )

    resp = client.get(
        "/api/v1/packaging/transactions?page=1&page_size=20",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert "items" in data
    assert "total" in data
    assert data["total"] > 0
    assert len(data["items"]) > 0
    tx = data["items"][0]
    assert "transaction_type" in tx
    assert "stock_before" in tx
    assert "stock_after" in tx


def test_packaging_consumption_rules_and_simulation(client):
    token = get_token_for(client)

    # 1. Create packaging items for rule
    bowl_resp = client.post(
        "/api/v1/packaging/items",
        json={
            "name": "Rule Test 500ml Bowl",
            "category": "CONTAINER",
            "material": "Food Grade PP",
            "capacity": "500ml",
            "unit": "pcs",
            "current_stock": 300.0,
            "minimum_stock": 50.0,
            "reorder_level": 100.0,
            "purchase_cost": 6.0,
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    bowl_id = bowl_resp.json()["data"]["id"]

    bag_resp = client.post(
        "/api/v1/packaging/items",
        json={
            "name": "Rule Test Kraft Bag",
            "category": "BAG",
            "material": "Kraft Paper",
            "unit": "pcs",
            "current_stock": 300.0,
            "minimum_stock": 50.0,
            "reorder_level": 100.0,
            "purchase_cost": 5.0,
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    bag_id = bag_resp.json()["data"]["id"]

    # 2. Create rules
    rule1_resp = client.post(
        "/api/v1/packaging/rules",
        json={
            "dish_category": "Dum Biryani",
            "portion_size": "500g",
            "packaging_item_id": bowl_id,
            "quantity_per_order_unit": 1.0,
            "description": "1 bowl per 500g Biryani",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert rule1_resp.status_code == 201

    rule2_resp = client.post(
        "/api/v1/packaging/rules",
        json={
            "dish_category": "ALL_ORDERS",
            "portion_size": "ALL",
            "packaging_item_id": bag_id,
            "quantity_per_order_unit": 1.0,
            "description": "1 delivery bag per order",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert rule2_resp.status_code == 201

    # 3. List rules
    rules_resp = client.get(
        "/api/v1/packaging/rules",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert rules_resp.status_code == 200
    rules = rules_resp.json()["data"]
    assert len(rules) >= 2

    # 4. Simulate order consumption
    sim_payload = {
        "items": [
            {"dish_category": "Dum Biryani", "portion_size": "500g", "quantity": 3},
        ]
    }
    sim_resp = client.post(
        "/api/v1/packaging/simulate-order-consumption",
        json=sim_payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert sim_resp.status_code == 200
    sim_data = sim_resp.json()["data"]
    assert "consumed_items" in sim_data
    assert "total_packaging_units" in sim_data
    assert "total_packaging_cost_inr" in sim_data
    # 3 bowls (3 * 6.0 = 18) + 3 bags (3 * 5.0 = 15) = 6 units, ₹33
    assert sim_data["total_packaging_units"] == 6.0
    assert sim_data["total_packaging_cost_inr"] == 33.0
