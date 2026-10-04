import requests
import json
import sys

BASE_URL = "http://localhost:8000/api/v1"

def test_phase6_e2e():
    print("=== Testing Phase 6 Menu Management & Pricing Rules E2E ===")

    # 1. Admin Authentication
    auth_resp = requests.post(f"{BASE_URL}/auth/login", json={"username_or_email": "admin", "password": "admin123"})
    assert auth_resp.status_code == 200, f"Login failed: {auth_resp.text}"
    token = auth_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    print("1. Admin authenticated successfully.")

    # 2. Menu Summary
    summary_resp = requests.get(f"{BASE_URL}/menu/summary", headers=headers)
    assert summary_resp.status_code == 200, f"Menu summary failed: {summary_resp.status_code}"
    summary = summary_resp.json()["data"]
    print("2. Menu Summary:", json.dumps(summary, indent=2))
    assert summary["total_items"] >= 19
    assert summary["total_categories"] >= 6
    assert summary["veg_items_count"] + summary["non_veg_items_count"] == summary["total_items"]

    # 3. List Categories
    cats_resp = requests.get(f"{BASE_URL}/menu/categories", headers=headers)
    assert cats_resp.status_code == 200
    categories = cats_resp.json()["data"]
    print(f"3. Retrieved {len(categories)} categories:")
    for c in categories:
        print(f"   - {c['name']} (Items: {c['items_count']}, slug: {c['slug']})")
    assert len(categories) >= 6

    # 4. Clean up previous test category if exists and Create Category
    for c in categories:
        if c["name"] == "Nawabi Thali Platters":
            requests.delete(f"{BASE_URL}/menu/categories/{c['id']}", headers=headers)

    cat_payload = {
        "name": "Nawabi Thali Platters",
        "description": "Complete meal platters served with biryani, salan, raita and dessert",
        "display_order": 7,
        "is_active": True,
    }
    create_cat_resp = requests.post(f"{BASE_URL}/menu/categories", json=cat_payload, headers=headers)
    assert create_cat_resp.status_code == 201, f"Create category failed: {create_cat_resp.text}"
    new_cat = create_cat_resp.json()["data"]
    new_cat_id = new_cat["id"]
    print(f"4. Created Category: {new_cat['name']} (ID: {new_cat_id}, Slug: {new_cat['slug']})")

    # 5. Create Menu Item with Portions & Platform Pricing Rules
    item_payload = {
        "category_id": new_cat_id,
        "name": "Panna Royal Shahi Feast Platter",
        "description": "Portion of Chicken Biryani, 2 Galouti Kebabs, Mirchi Salan, Burani Raita and Rabdi Jamun",
        "is_veg": False,
        "spice_level": "MEDIUM",
        "preparation_time_minutes": 25,
        "is_available": True,
        "is_active": True,
        "display_order": 1,
        "portions": [
            {
                "portion_size": "Standard Feast",
                "weight_grams": 750,
                "serves_persons": "1 Person",
                "cost_price": 180.0,
                "base_price": 450.0,
                # Omit zomato_price and swiggy_price to verify auto-calculation
            },
            {
                "portion_size": "Jumbo Royal Feast",
                "weight_grams": 1500,
                "serves_persons": "2-3 Persons",
                "cost_price": 340.0,
                "base_price": 850.0,
                "zomato_price": 1050.0, # custom override
                "swiggy_price": 1020.0, # custom override
            }
        ],
    }
    create_item_resp = requests.post(f"{BASE_URL}/menu/items", json=item_payload, headers=headers)
    assert create_item_resp.status_code == 201, f"Create item failed: {create_item_resp.text}"
    item_data = create_item_resp.json()["data"]
    new_item_id = item_data["id"]
    print(f"5. Created Dish: {item_data['name']} (Starting price: INR {item_data['starting_price']})")
    assert len(item_data["portions"]) == 2

    # Check Portion 1 auto markup: 450 * 1.22 = 549, 450 * 1.20 = 540
    p1 = item_data["portions"][0]
    print(f"   Portion 1: Base: INR {p1['base_price']}, Zomato (+22%): INR {p1['zomato_price']}, Swiggy (+20%): INR {p1['swiggy_price']}, Margin: {p1['profit_margin_percent']}%")
    assert p1["base_price"] == 450.0
    assert p1["zomato_price"] == 549.0
    assert p1["swiggy_price"] == 540.0
    assert p1["profit_margin_percent"] == 60.0

    # 6. Filter Menu Items
    filtered_resp = requests.get(f"{BASE_URL}/menu/items?category_id={new_cat_id}", headers=headers)
    assert filtered_resp.status_code == 200
    filtered_items = filtered_resp.json()["data"]
    assert len(filtered_items) == 1
    assert filtered_items[0]["id"] == new_item_id
    print(f"6. Filtered by category successfully (Found {len(filtered_items)} item).")

    # 7. Fast 1-click in-stock / out-of-stock toggle
    toggle_resp = requests.patch(f"{BASE_URL}/menu/items/{new_item_id}/availability", json={"is_available": False}, headers=headers)
    assert toggle_resp.status_code == 200
    assert toggle_resp.json()["data"]["is_available"] is False
    print(f"7a. Toggled item {new_item_id} to Out of Stock.")

    summary_after = requests.get(f"{BASE_URL}/menu/summary", headers=headers).json()["data"]
    assert summary_after["out_of_stock_count"] >= 1

    toggle_back_resp = requests.patch(f"{BASE_URL}/menu/items/{new_item_id}/availability", json={"is_available": True}, headers=headers)
    assert toggle_back_resp.status_code == 200
    assert toggle_back_resp.json()["data"]["is_available"] is True
    print(f"7b. Toggled item {new_item_id} back to In Stock.")

    # 8. Platform Price Calculation Endpoint
    calc_resp = requests.post(f"{BASE_URL}/menu/calculate-prices", json={"base_price": 500.0}, headers=headers)
    assert calc_resp.status_code == 200
    calc = calc_resp.json()["data"]
    print("8. Platform Price Calculator:", calc)
    assert calc["website_price"] == 500.0
    assert calc["zomato_price"] == 610.0
    assert calc["swiggy_price"] == 600.0

    # 9. Public Customer Menu Endpoint
    public_menu_resp = requests.get(f"{BASE_URL}/public/menu")
    assert public_menu_resp.status_code == 200
    public_menu = public_menu_resp.json()["data"]
    print(f"9. Public Storefront Menu fetched without auth: {len(public_menu)} categories returned.")
    assert len(public_menu) >= 6

    # 10. Clean up created test item and category
    del_item = requests.delete(f"{BASE_URL}/menu/items/{new_item_id}", headers=headers)
    assert del_item.status_code == 200
    del_cat = requests.delete(f"{BASE_URL}/menu/categories/{new_cat_id}", headers=headers)
    assert del_cat.status_code == 200
    print(f"10. Cleaned up test item and category successfully.")

    print("\n ALL PHASE 6 E2E TESTS PASSED SUCCESSFULLY!")

if __name__ == "__main__":
    test_phase6_e2e()
