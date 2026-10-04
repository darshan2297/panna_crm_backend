import pytest
from app.services.seed_service import seed_dashboard_data


def get_token_for(client, username, password):
    resp = client.post(
        "/api/v1/auth/login",
        json={"username_or_email": username, "password": password},
    )
    assert resp.status_code == 200
    return resp.json()["access_token"]


def test_dashboard_stats_authenticated(client, db):
    # Ensure data is seeded in test db
    seed_dashboard_data(db)

    token = get_token_for(client, "admin", "admin123")
    response = client.get(
        "/api/v1/dashboard/stats",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    data = body["data"]

    # Verify KPIs
    assert "kpis" in data
    assert data["kpis"]["total_orders"] >= 1
    assert "platform_orders" in data["kpis"]
    assert "platform_sales" in data["kpis"]

    # Verify Trends & Charts
    assert "sales_trend" in data
    assert len(data["sales_trend"]) == 7

    # Verify Top Items
    assert "top_selling_items" in data
    assert len(data["top_selling_items"]) >= 1

    # Verify Low Stock
    assert "low_stock_alerts" in data

    # Verify Recent Orders
    assert "recent_orders" in data
    assert len(data["recent_orders"]) >= 1


def test_dashboard_unauthenticated(client):
    response = client.get("/api/v1/dashboard/stats")
    assert response.status_code == 401


def test_dashboard_recent_orders(client, db):
    seed_dashboard_data(db)
    token = get_token_for(client, "staff", "staff123")
    response = client.get(
        "/api/v1/dashboard/recent-orders",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()["data"]
    assert isinstance(data, list)
    assert len(data) >= 1
    first_order = data[0]
    assert "order_number" in first_order
    assert "platform" in first_order
    assert "total_amount" in first_order
