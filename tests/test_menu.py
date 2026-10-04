import pytest


def get_token_for(client, username="admin", password="admin123"):
    resp = client.post(
        "/api/v1/auth/login",
        json={"username_or_email": username, "password": password},
    )
    assert resp.status_code == 200, f"Login failed: {resp.text}"
    return resp.json()["access_token"]


def test_menu_summary(client):
    token = get_token_for(client)
    resp = client.get(
        "/api/v1/menu/summary",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert "total_items" in data["data"]
    assert "total_categories" in data["data"]
    assert "veg_items_count" in data["data"]
    assert "non_veg_items_count" in data["data"]


def test_create_and_list_categories(client):
    token = get_token_for(client)

    # 1. Create Category
    cat_payload = {
        "name": "Dum Biryani Specialties",
        "description": "Authentic Nizami slow cooked handi biryani dishes",
        "display_order": 1,
        "is_active": True,
    }
    create_resp = client.post(
        "/api/v1/menu/categories",
        json=cat_payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert create_resp.status_code == 201
    cat_data = create_resp.json()["data"]
    assert cat_data["name"] == "Dum Biryani Specialties"
    assert cat_data["slug"] == "dum-biryani-specialties"
    cat_id = cat_data["id"]

    # 2. List Categories
    list_resp = client.get(
        "/api/v1/menu/categories",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert list_resp.status_code == 200
    cats = list_resp.json()["data"]
    assert any(c["id"] == cat_id for c in cats)


def test_create_menu_item_with_portions_and_auto_platform_prices(client):
    token = get_token_for(client)

    # First get or create category
    cat_resp = client.post(
        "/api/v1/menu/categories",
        json={"name": "Special Kebabs", "description": "Smoked tandoor starters", "display_order": 2},
        headers={"Authorization": f"Bearer {token}"},
    )
    cat_id = cat_resp.json()["data"]["id"]

    item_payload = {
        "category_id": cat_id,
        "name": "Panna Murgh Malai Tikka",
        "description": "Creamy boneless chicken marinated in cardamom, cashew paste and hung curd",
        "is_veg": False,
        "spice_level": "MILD",
        "preparation_time_minutes": 20,
        "is_available": True,
        "is_active": True,
        "display_order": 1,
        "portions": [
            {
                "portion_size": "Half (4 pcs)",
                "weight_grams": 200,
                "serves_persons": "1 Person",
                "cost_price": 90.0,
                "base_price": 220.0,
                # zomato and swiggy price omitted to test auto platform markup
            },
            {
                "portion_size": "Full (8 pcs)",
                "weight_grams": 400,
                "serves_persons": "2-3 Persons",
                "cost_price": 160.0,
                "base_price": 399.0,
                "zomato_price": 489.0, # custom override
                "swiggy_price": 479.0, # custom override
            }
        ],
    }

    create_resp = client.post(
        "/api/v1/menu/items",
        json=item_payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert create_resp.status_code == 201
    item = create_resp.json()["data"]
    assert item["name"] == "Panna Murgh Malai Tikka"
    assert item["starting_price"] == 220.0
    assert len(item["portions"]) == 2

    # Verify auto platform markup on portion 0 (base=220: Zomato +22% = 268, Swiggy +20% = 264)
    p0 = item["portions"][0]
    assert p0["base_price"] == 220.0
    assert p0["zomato_price"] == 268.0
    assert p0["swiggy_price"] == 264.0
    # Profit margin: ((220 - 90) / 220) * 100 = 59.1%
    assert p0["profit_margin_percent"] > 50.0

    # Verify custom override on portion 1
    p1 = item["portions"][1]
    assert p1["base_price"] == 399.0
    assert p1["zomato_price"] == 489.0
    assert p1["swiggy_price"] == 479.0


def test_toggle_item_availability_fast(client):
    token = get_token_for(client)

    # Create category and item
    cat_resp = client.post(
        "/api/v1/menu/categories",
        json={"name": "Dessert Treats", "display_order": 5},
        headers={"Authorization": f"Bearer {token}"},
    )
    cat_id = cat_resp.json()["data"]["id"]

    item_resp = client.post(
        "/api/v1/menu/items",
        json={
            "category_id": cat_id,
            "name": "Kesar Rabdi Jamun",
            "is_veg": True,
            "portions": [{"portion_size": "2 pcs", "cost_price": 30.0, "base_price": 120.0}],
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    item_id = item_resp.json()["data"]["id"]
    assert item_resp.json()["data"]["is_available"] is True

    # 1. Toggle to Out of Stock
    toggle_resp = client.patch(
        f"/api/v1/menu/items/{item_id}/availability",
        json={"is_available": False},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert toggle_resp.status_code == 200
    assert toggle_resp.json()["data"]["is_available"] is False

    # 2. Toggle back to In Stock
    toggle_back_resp = client.patch(
        f"/api/v1/menu/items/{item_id}/availability",
        json={"is_available": True},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert toggle_back_resp.status_code == 200
    assert toggle_back_resp.json()["data"]["is_available"] is True


def test_calculate_platform_prices(client):
    token = get_token_for(client)
    resp = client.post(
        "/api/v1/menu/calculate-prices",
        json={"base_price": 500.0},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["base_price"] == 500.0
    assert data["website_price"] == 500.0
    assert data["zomato_price"] == 610.0  # round(500 * 1.22)
    assert data["swiggy_price"] == 600.0  # round(500 * 1.20)


def test_public_menu_endpoint_unauthenticated(client):
    # Customer storefronts can fetch the active and available menu without staff auth
    resp = client.get("/api/v1/public/menu")
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert isinstance(data["data"], list)
