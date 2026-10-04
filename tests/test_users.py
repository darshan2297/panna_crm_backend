import pytest


def get_token_for(client, username, password):
    resp = client.post(
        "/api/v1/auth/login",
        json={"username_or_email": username, "password": password},
    )
    assert resp.status_code == 200
    return resp.json()["access_token"]


def test_admin_list_users(client):
    admin_token = get_token_for(client, "admin", "admin123")
    response = client.get(
        "/api/v1/users",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 1
    assert len(data["items"]) >= 1


def test_staff_cannot_list_users(client):
    staff_token = get_token_for(client, "staff", "staff123")
    response = client.get(
        "/api/v1/users",
        headers={"Authorization": f"Bearer {staff_token}"},
    )
    assert response.status_code == 403


def test_admin_create_user_and_conflict(client):
    admin_token = get_token_for(client, "admin", "admin123")

    # Create new user
    new_user_data = {
        "email": "chef1@pannabiryani.com",
        "username": "chef1",
        "full_name": "Head Biryani Chef",
        "phone": "+91 9999988888",
        "role": "STAFF",
        "password": "chefpassword123",
        "is_active": True,
    }
    create_resp = client.post(
        "/api/v1/users",
        headers={"Authorization": f"Bearer {admin_token}"},
        json=new_user_data,
    )
    assert create_resp.status_code == 201
    created = create_resp.json()["data"]
    assert created["username"] == "chef1"
    assert created["role"] == "STAFF"

    # Duplicate create should return 409
    dup_resp = client.post(
        "/api/v1/users",
        headers={"Authorization": f"Bearer {admin_token}"},
        json=new_user_data,
    )
    assert dup_resp.status_code == 409


def test_admin_cannot_delete_self(client):
    admin_token = get_token_for(client, "admin", "admin123")
    # Get admin user ID
    me_resp = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    admin_id = me_resp.json()["data"]["id"]

    # Try to delete self
    del_resp = client.delete(
        f"/api/v1/users/{admin_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert del_resp.status_code == 403


def test_change_password(client):
    admin_token = get_token_for(client, "admin", "admin123")

    # Change password with wrong old password
    fail_resp = client.post(
        "/api/v1/auth/change-password",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"old_password": "wrongpassword", "new_password": "newadminpass123"},
    )
    assert fail_resp.status_code == 401

    # Change password successfully
    success_resp = client.post(
        "/api/v1/auth/change-password",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"old_password": "admin123", "new_password": "newadminpass123"},
    )
    assert success_resp.status_code == 200

    # Verify login with new password
    new_token = get_token_for(client, "admin", "newadminpass123")
    assert new_token is not None

    # Reset back to admin123
    client.post(
        "/api/v1/auth/change-password",
        headers={"Authorization": f"Bearer {new_token}"},
        json={"old_password": "newadminpass123", "new_password": "admin123"},
    )


def test_update_profile(client):
    admin_token = get_token_for(client, "admin", "admin123")
    update_resp = client.patch(
        "/api/v1/auth/profile",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"full_name": "Panna Executive Master Admin", "phone": "+91 9999900000"},
    )
    assert update_resp.status_code == 200
    data = update_resp.json()["data"]
    assert data["full_name"] == "Panna Executive Master Admin"
    assert data["phone"] == "+91 9999900000"
