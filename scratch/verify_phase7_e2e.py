import requests
import sys

BASE_URL = "http://127.0.0.1:8000/api/v1"

def run_e2e():
    print("=== STARTING PHASE 7 INVENTORY E2E VERIFICATION ===")

    # 1. Login
    login_resp = requests.post(
        f"{BASE_URL}/auth/login",
        json={"username_or_email": "admin", "password": "admin123"},
    )
    assert login_resp.status_code == 200, f"Login failed: {login_resp.text}"
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    print("[PASS] 1. Admin login successful")

    # 2. Get Summary
    sum_resp = requests.get(f"{BASE_URL}/inventory/summary", headers=headers)
    assert sum_resp.status_code == 200, f"Summary failed: {sum_resp.text}"
    summary = sum_resp.json()["data"]
    print(f"[PASS] 2. Inventory Summary retrieved: Total Items: {summary['total_items']}, "
          f"In Stock: {summary['in_stock_items']}, Low Stock: {summary['low_stock_items']}, "
          f"Total Valuation: INR {summary['total_inventory_value_inr']}")
    assert summary["total_items"] > 0
    assert summary["total_inventory_value_inr"] > 0

    # 3. List Items
    items_resp = requests.get(f"{BASE_URL}/inventory/items", headers=headers)
    assert items_resp.status_code == 200, f"List items failed: {items_resp.text}"
    items_data = items_resp.json()["data"]
    print(f"[PASS] 3. Listed {len(items_data['items'])} items (Total: {items_data['total']})")

    # 4. Create New Item
    new_item_payload = {
        "name": "E2E Test Mace Flower (Javitri)",
        "sku": "ING-SPICE-E2E01",
        "category": "SPICE",
        "unit": "kg",
        "current_stock": 4.0,
        "minimum_stock": 1.5,
        "reorder_level": 3.0,
        "purchase_price": 1800.0,
        "supplier": "Spice Route Corp",
        "storage_location": "Aroma Cabinet 1",
        "description": "Exotic warm mace blades for handi dum biryani pot layering",
    }
    create_resp = requests.post(f"{BASE_URL}/inventory/items", json=new_item_payload, headers=headers)
    assert create_resp.status_code == 201, f"Create item failed: {create_resp.text}"
    created_item = create_resp.json()["data"]
    item_id = created_item["id"]
    print(f"[PASS] 4. Created Item #{item_id}: {created_item['name']}, Valuation: INR {created_item['total_valuation']}")

    # 5. Stock-In (Purchase)
    stock_in_resp = requests.post(
        f"{BASE_URL}/inventory/items/{item_id}/adjust",
        json={
            "transaction_type": "STOCK_IN",
            "quantity": 6.0,
            "unit_price": 1800.0,
            "reference_no": "PO-E2E-99",
            "notes": "Restocked 6kg premium Javitri",
        },
        headers=headers,
    )
    assert stock_in_resp.status_code == 200, f"Stock in failed: {stock_in_resp.text}"
    tx_in = stock_in_resp.json()["data"]
    assert tx_in["stock_after"] == 10.0
    print(f"[PASS] 5. Stock-In 6kg: Balance {tx_in['stock_before']} -> {tx_in['stock_after']} kg")

    # 6. Stock-Out (Consumption)
    stock_out_resp = requests.post(
        f"{BASE_URL}/inventory/items/{item_id}/adjust",
        json={
            "transaction_type": "STOCK_OUT",
            "quantity": 2.5,
            "reference_no": "KITCHEN-POT-01",
            "notes": "Issued for chef spice blend",
        },
        headers=headers,
    )
    assert stock_out_resp.status_code == 200, f"Stock out failed: {stock_out_resp.text}"
    tx_out = stock_out_resp.json()["data"]
    assert tx_out["stock_after"] == 7.5
    print(f"[PASS] 6. Stock-Out 2.5kg: Balance {tx_out['stock_before']} -> {tx_out['stock_after']} kg")

    # 7. Wastage
    waste_resp = requests.post(
        f"{BASE_URL}/inventory/items/{item_id}/adjust",
        json={
            "transaction_type": "WASTAGE",
            "quantity": 0.5,
            "reference_no": "WASTE-009",
            "notes": "Spill during weighing",
        },
        headers=headers,
    )
    assert waste_resp.status_code == 200, f"Wastage failed: {waste_resp.text}"
    tx_waste = waste_resp.json()["data"]
    assert tx_waste["stock_after"] == 7.0
    print(f"[PASS] 7. Wastage 0.5kg: Balance {tx_waste['stock_before']} -> {tx_waste['stock_after']} kg")

    # 8. List Transactions
    tx_list_resp = requests.get(f"{BASE_URL}/inventory/transactions?item_id={item_id}", headers=headers)
    assert tx_list_resp.status_code == 200, f"List transactions failed: {tx_list_resp.text}"
    tx_items = tx_list_resp.json()["data"]["items"]
    print(f"[PASS] 8. Retrieved {len(tx_items)} transactions for Item #{item_id}")
    assert len(tx_items) >= 3

    # 9. Clean up test item
    del_resp = requests.delete(f"{BASE_URL}/inventory/items/{item_id}", headers=headers)
    assert del_resp.status_code == 200, f"Delete failed: {del_resp.text}"
    print(f"[PASS] 9. Soft-deleted item #{item_id}")

    print("\n=== ALL PHASE 7 BACKEND E2E TESTS PASSED SUCCESSFULLY! ===")

if __name__ == "__main__":
    run_e2e()
