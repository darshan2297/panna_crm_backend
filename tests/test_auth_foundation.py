def test_login_success(client):
    response = client.post(
        "/api/v1/auth/login",
        json={"username_or_email": "admin", "password": "admin123"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"


def test_login_failure(client):
    response = client.post(
        "/api/v1/auth/login",
        json={"username_or_email": "admin", "password": "wrongpassword"},
    )
    assert response.status_code == 401


def test_get_current_user_profile(client):
    # Step 1: Login
    login_resp = client.post(
        "/api/v1/auth/login",
        json={"username_or_email": "admin", "password": "admin123"},
    )
    token = login_resp.json()["access_token"]

    # Step 2: Fetch profile
    profile_resp = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert profile_resp.status_code == 200
    body = profile_resp.json()
    assert body["success"] is True
    assert body["data"]["username"] == "admin"
    assert body["data"]["role"] == "ADMIN"
