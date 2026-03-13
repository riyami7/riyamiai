"""Integration tests for authentication endpoints."""

import pytest
from fastapi.testclient import TestClient


class TestAuthLogin:
    """Test authentication login endpoint."""

    created_user_id: int | None = None

    @pytest.fixture(autouse=True)
    def setup_and_teardown(self, client: TestClient, admin_user: dict):
        """Setup: create a user (via admin) for auth tests. Teardown: delete it."""
        # Setup - create a user via admin
        response = client.post(
            "/users/",
            json={
                "email": "authtest@example.com",
                "name": "Auth Test User",
                "password": "securepassword123",
                "is_active": True,
            },
            headers=admin_user["headers"],
        )
        if response.status_code == 201:
            TestAuthLogin.created_user_id = response.json()["id"]

        yield

        # Teardown - delete the user if it exists
        if TestAuthLogin.created_user_id is not None:
            client.delete(
                f"/users/{TestAuthLogin.created_user_id}",
                headers=admin_user["headers"],
            )
            TestAuthLogin.created_user_id = None

    def test_login_success(self, client: TestClient):
        """Test successful login returns access token."""
        response = client.post("/auth/login", json={
            "email": "authtest@example.com",
            "password": "securepassword123",
        })

        assert response.status_code == 200
        data = response.json()

        assert "access_token" in data
        assert "token_type" in data
        assert data["token_type"] == "bearer"
        assert len(data["access_token"]) > 0

    def test_login_wrong_password(self, client: TestClient):
        """Test login with wrong password returns 401."""
        response = client.post("/auth/login", json={
            "email": "authtest@example.com",
            "password": "wrongpassword",
        })

        assert response.status_code == 401
        data = response.json()
        assert data["error_code"] == "INVALID_CREDENTIALS"

    def test_login_nonexistent_user(self, client: TestClient):
        """Test login with nonexistent email returns 401."""
        response = client.post("/auth/login", json={
            "email": "nonexistent@example.com",
            "password": "securepassword123",
        })

        assert response.status_code == 401
        data = response.json()
        assert data["error_code"] == "INVALID_CREDENTIALS"

    def test_login_invalid_email_format(self, client: TestClient):
        """Test login with invalid email format returns 422."""
        response = client.post("/auth/login", json={
            "email": "not-an-email",
            "password": "securepassword123",
        })

        assert response.status_code == 422
        data = response.json()
        assert data["error_code"] == "VALIDATION_ERROR"

    def test_login_missing_password(self, client: TestClient):
        """Test login without password returns 422."""
        response = client.post("/auth/login", json={
            "email": "authtest@example.com",
        })

        assert response.status_code == 422
        data = response.json()
        assert data["error_code"] == "VALIDATION_ERROR"

    def test_login_missing_email(self, client: TestClient):
        """Test login without email returns 422."""
        response = client.post("/auth/login", json={
            "password": "securepassword123",
        })

        assert response.status_code == 422
        data = response.json()
        assert data["error_code"] == "VALIDATION_ERROR"


class TestAuthLoginDisabledUser:
    """Test authentication for disabled users."""

    created_user_id: int | None = None

    @pytest.fixture(autouse=True)
    def setup_and_teardown(self, client: TestClient, admin_user: dict):
        """Setup: create a disabled user via admin. Teardown: delete it."""
        # Setup - create a disabled user via admin
        response = client.post(
            "/users/",
            json={
                "email": "disabled@example.com",
                "name": "Disabled User",
                "password": "securepassword123",
                "is_active": False,
            },
            headers=admin_user["headers"],
        )
        if response.status_code == 201:
            TestAuthLoginDisabledUser.created_user_id = response.json()["id"]

        yield

        # Teardown - delete the user via admin
        if TestAuthLoginDisabledUser.created_user_id is not None:
            client.delete(
                f"/users/{TestAuthLoginDisabledUser.created_user_id}",
                headers=admin_user["headers"],
            )
            TestAuthLoginDisabledUser.created_user_id = None

    def test_login_disabled_user(self, client: TestClient):
        """Test login with disabled user returns 401."""
        response = client.post("/auth/login", json={
            "email": "disabled@example.com",
            "password": "securepassword123",
        })

        assert response.status_code == 401
        data = response.json()
        assert data["error_code"] == "USER_DISABLED"


class TestAuthMe:
    """Test GET /auth/me endpoint."""

    created_user_id: int | None = None
    auth_token: str | None = None

    @pytest.fixture(autouse=True)
    def setup_and_teardown(self, client: TestClient, admin_user: dict):
        """Setup: create a user via admin and get token. Teardown: delete user."""
        # Setup - create a user via admin
        response = client.post(
            "/users/",
            json={
                "email": "metest@example.com",
                "name": "Me Test User",
                "password": "securepassword123",
                "is_active": True,
            },
            headers=admin_user["headers"],
        )
        if response.status_code == 201:
            TestAuthMe.created_user_id = response.json()["id"]
            # Get auth token
            login_response = client.post("/auth/login", json={
                "email": "metest@example.com",
                "password": "securepassword123",
            })
            if login_response.status_code == 200:
                TestAuthMe.auth_token = login_response.json()["access_token"]

        yield

        # Teardown - delete the user via admin
        if TestAuthMe.created_user_id is not None:
            client.delete(
                f"/users/{TestAuthMe.created_user_id}",
                headers=admin_user["headers"],
            )
            TestAuthMe.created_user_id = None
            TestAuthMe.auth_token = None

    def test_get_me_success(self, client: TestClient):
        """Test getting current user profile with valid token."""
        assert TestAuthMe.auth_token is not None

        response = client.get(
            "/auth/me",
            headers={"Authorization": f"Bearer {TestAuthMe.auth_token}"}
        )

        assert response.status_code == 200
        data = response.json()

        assert data["id"] == TestAuthMe.created_user_id
        assert data["email"] == "metest@example.com"
        assert data["name"] == "Me Test User"
        assert data["is_active"] is True
        assert data["role"] == "user"
        assert "password" not in data
        assert "hashed_password" not in data

    def test_get_me_without_token(self, client: TestClient):
        """Test getting current user without token returns 401 or 403."""
        response = client.get("/auth/me")

        # HTTPBearer returns 401/403 depending on the issue
        assert response.status_code in [401, 403]

    def test_get_me_with_invalid_token(self, client: TestClient):
        """Test getting current user with invalid token returns 401."""
        response = client.get(
            "/auth/me",
            headers={"Authorization": "Bearer invalid_token"}
        )

        assert response.status_code == 401
        data = response.json()
        assert data["error_code"] == "INVALID_TOKEN"

    def test_get_me_with_malformed_header(self, client: TestClient):
        """Test getting current user with malformed header returns 401 or 403."""
        response = client.get(
            "/auth/me",
            headers={"Authorization": "NotBearer token"}
        )

        # HTTPBearer returns 401/403 depending on the issue
        assert response.status_code in [401, 403]
