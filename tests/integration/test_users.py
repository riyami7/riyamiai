"""Integration tests for user CRUD endpoints."""

import pytest
from fastapi.testclient import TestClient


def get_auth_headers(client: TestClient, email: str, password: str) -> dict:
    """Helper to get authentication headers."""
    response = client.post("/auth/login", json={
        "email": email,
        "password": password,
    })
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


class TestUserCRUD:
    """Test user CRUD operations in sequence.

    Tests are ordered to create a user (via admin), perform operations, and clean up.
    Uses class-level state to track the created user ID across tests.
    """

    created_user_id: int | None = None
    created_user_email: str | None = None
    user_auth_headers: dict | None = None

    def test_create_user(self, client: TestClient, admin_user: dict, test_user_data: dict):
        """Test creating a new user (admin only)."""
        response = client.post(
            "/users/",
            json=test_user_data,
            headers=admin_user["headers"],
        )

        assert response.status_code == 201
        data = response.json()

        assert data["email"] == test_user_data["email"]
        assert data["name"] == test_user_data["name"]
        assert data["is_active"] == test_user_data["is_active"]
        assert data["role"] == "user"
        assert "id" in data
        assert "created_at" in data
        assert "updated_at" in data

        # Password should never be in the response
        assert "password" not in data
        assert "hashed_password" not in data

        # Store the user ID and email for subsequent tests
        TestUserCRUD.created_user_id = data["id"]
        TestUserCRUD.created_user_email = test_user_data["email"]

        # Get auth token for the created user (for subsequent tests)
        TestUserCRUD.user_auth_headers = get_auth_headers(
            client,
            test_user_data["email"],
            test_user_data["password"]
        )

    def test_create_user_with_admin_role(self, client: TestClient, admin_user: dict):
        """Test creating a user with admin role."""
        response = client.post(
            "/users/",
            json={
                "email": "newadmin@example.com",
                "name": "New Admin",
                "password": "securepassword123",
                "is_active": True,
                "role": "admin",
            },
            headers=admin_user["headers"],
        )

        assert response.status_code == 201
        data = response.json()
        assert data["role"] == "admin"

        # Clean up
        client.delete(
            f"/users/{data['id']}",
            headers=admin_user["headers"],
        )

    def test_get_user(self, client: TestClient):
        """Test getting a user by ID (auth required - user role)."""
        assert TestUserCRUD.created_user_id is not None
        assert TestUserCRUD.user_auth_headers is not None

        response = client.get(
            f"/users/{TestUserCRUD.created_user_id}",
            headers=TestUserCRUD.user_auth_headers
        )

        assert response.status_code == 200
        data = response.json()

        assert data["id"] == TestUserCRUD.created_user_id
        assert data["email"] == TestUserCRUD.created_user_email
        assert data["role"] == "user"

    def test_list_users(self, client: TestClient):
        """Test listing users (auth required - user role)."""
        assert TestUserCRUD.user_auth_headers is not None

        response = client.get("/users/", headers=TestUserCRUD.user_auth_headers)

        assert response.status_code == 200
        data = response.json()

        assert "users" in data
        assert "total" in data
        assert data["total"] >= 1

        # Verify our created user is in the list
        user_ids = [user["id"] for user in data["users"]]
        assert TestUserCRUD.created_user_id in user_ids

        # Verify role is present in response
        for user in data["users"]:
            assert "role" in user

    def test_list_users_pagination(self, client: TestClient):
        """Test listing users with pagination (auth required)."""
        assert TestUserCRUD.user_auth_headers is not None

        response = client.get(
            "/users/?skip=0&limit=1",
            headers=TestUserCRUD.user_auth_headers
        )

        assert response.status_code == 200
        data = response.json()

        assert len(data["users"]) <= 1

    def test_update_user(self, client: TestClient, test_user_update_data: dict):
        """Test updating a user (auth required - user role)."""
        assert TestUserCRUD.created_user_id is not None
        assert TestUserCRUD.user_auth_headers is not None

        response = client.put(
            f"/users/{TestUserCRUD.created_user_id}",
            json=test_user_update_data,
            headers=TestUserCRUD.user_auth_headers
        )

        assert response.status_code == 200
        data = response.json()

        assert data["id"] == TestUserCRUD.created_user_id
        assert data["name"] == test_user_update_data["name"]
        assert data["is_active"] == test_user_update_data["is_active"]

    def test_update_user_partial(self, client: TestClient):
        """Test partial update of a user (auth required)."""
        assert TestUserCRUD.created_user_id is not None
        assert TestUserCRUD.user_auth_headers is not None

        response = client.put(
            f"/users/{TestUserCRUD.created_user_id}",
            json={"name": "Partially Updated User"},
            headers=TestUserCRUD.user_auth_headers
        )

        assert response.status_code == 200
        data = response.json()

        assert data["name"] == "Partially Updated User"

    def test_delete_user(self, client: TestClient, admin_user: dict):
        """Test deleting a user (auth required - using admin to delete)."""
        assert TestUserCRUD.created_user_id is not None

        response = client.delete(
            f"/users/{TestUserCRUD.created_user_id}",
            headers=admin_user["headers"]
        )

        assert response.status_code == 204

    def test_get_deleted_user(self, client: TestClient):
        """Test that accessing with deleted user's token returns 401.

        After the user is deleted, their JWT token becomes invalid because
        the user no longer exists in the database. This results in 401.
        """
        assert TestUserCRUD.created_user_id is not None
        assert TestUserCRUD.user_auth_headers is not None

        response = client.get(
            f"/users/{TestUserCRUD.created_user_id}",
            headers=TestUserCRUD.user_auth_headers
        )

        # Token belongs to deleted user, so auth fails
        assert response.status_code == 401
        data = response.json()
        assert data["error_code"] == "USER_NOT_FOUND"


class TestUserErrors:
    """Test error cases for user endpoints."""

    created_user_id: int | None = None
    user_auth_headers: dict | None = None

    @pytest.fixture(autouse=True)
    def setup_and_teardown(self, client: TestClient, admin_user: dict):
        """Setup: create a user (via admin) for error tests. Teardown: delete it."""
        # Setup - create a user via admin
        response = client.post(
            "/users/",
            json={
                "email": "errortest@example.com",
                "name": "Error Test User",
                "password": "securepassword123",
                "is_active": True,
            },
            headers=admin_user["headers"],
        )
        if response.status_code == 201:
            TestUserErrors.created_user_id = response.json()["id"]
            TestUserErrors.user_auth_headers = get_auth_headers(
                client,
                "errortest@example.com",
                "securepassword123"
            )

        yield

        # Teardown - delete the user if it exists
        if TestUserErrors.created_user_id is not None:
            client.delete(
                f"/users/{TestUserErrors.created_user_id}",
                headers=admin_user["headers"]
            )
            TestUserErrors.created_user_id = None
            TestUserErrors.user_auth_headers = None

    def test_create_duplicate_email(self, client: TestClient, admin_user: dict):
        """Test creating a user with duplicate email returns 409."""
        response = client.post(
            "/users/",
            json={
                "email": "errortest@example.com",
                "name": "Duplicate User",
                "password": "securepassword123",
                "is_active": True,
            },
            headers=admin_user["headers"],
        )

        assert response.status_code == 409
        data = response.json()
        assert data["error_code"] == "EMAIL_ALREADY_EXISTS"

    def test_get_nonexistent_user(self, client: TestClient):
        """Test getting a nonexistent user returns 404."""
        response = client.get(
            "/users/999999",
            headers=TestUserErrors.user_auth_headers
        )

        assert response.status_code == 404
        data = response.json()
        assert data["error_code"] == "USER_NOT_FOUND"

    def test_update_nonexistent_user(self, client: TestClient):
        """Test updating a nonexistent user returns 404."""
        response = client.put(
            "/users/999999",
            json={"name": "Ghost"},
            headers=TestUserErrors.user_auth_headers
        )

        assert response.status_code == 404
        data = response.json()
        assert data["error_code"] == "USER_NOT_FOUND"

    def test_delete_nonexistent_user(self, client: TestClient):
        """Test deleting a nonexistent user returns 404."""
        response = client.delete(
            "/users/999999",
            headers=TestUserErrors.user_auth_headers
        )

        assert response.status_code == 404
        data = response.json()
        assert data["error_code"] == "USER_NOT_FOUND"

    def test_create_user_invalid_email(self, client: TestClient, admin_user: dict):
        """Test creating a user with invalid email returns 422."""
        response = client.post(
            "/users/",
            json={
                "email": "not-an-email",
                "name": "Invalid Email User",
                "password": "securepassword123",
                "is_active": True,
            },
            headers=admin_user["headers"],
        )

        assert response.status_code == 422
        data = response.json()
        assert data["error_code"] == "VALIDATION_ERROR"

    def test_create_user_missing_required_field(self, client: TestClient, admin_user: dict):
        """Test creating a user with missing required fields returns 422."""
        response = client.post(
            "/users/",
            json={
                "email": "missingname@example.com",
                "password": "securepassword123",
            },
            headers=admin_user["headers"],
        )

        assert response.status_code == 422
        data = response.json()
        assert data["error_code"] == "VALIDATION_ERROR"

    def test_create_user_password_too_short(self, client: TestClient, admin_user: dict):
        """Test creating a user with too short password returns 422."""
        response = client.post(
            "/users/",
            json={
                "email": "shortpass@example.com",
                "name": "Short Password User",
                "password": "short",
                "is_active": True,
            },
            headers=admin_user["headers"],
        )

        assert response.status_code == 422
        data = response.json()
        assert data["error_code"] == "VALIDATION_ERROR"

    def test_create_user_missing_password(self, client: TestClient, admin_user: dict):
        """Test creating a user without password returns 422."""
        response = client.post(
            "/users/",
            json={
                "email": "nopass@example.com",
                "name": "No Password User",
                "is_active": True,
            },
            headers=admin_user["headers"],
        )

        assert response.status_code == 422
        data = response.json()
        assert data["error_code"] == "VALIDATION_ERROR"

    def test_update_user_duplicate_email(self, client: TestClient, admin_user: dict):
        """Test updating a user with duplicate email returns 409."""
        # Create another user via admin
        response = client.post(
            "/users/",
            json={
                "email": "another@example.com",
                "name": "Another User",
                "password": "securepassword123",
                "is_active": True,
            },
            headers=admin_user["headers"],
        )
        assert response.status_code == 201
        another_user_id = response.json()["id"]

        try:
            # Try to update with existing email
            response = client.put(
                f"/users/{another_user_id}",
                json={"email": "errortest@example.com"},
                headers=TestUserErrors.user_auth_headers
            )

            assert response.status_code == 409
            data = response.json()
            assert data["error_code"] == "EMAIL_ALREADY_EXISTS"
        finally:
            # Clean up
            client.delete(
                f"/users/{another_user_id}",
                headers=admin_user["headers"]
            )


class TestRBAC:
    """Test role-based access control."""

    created_user_id: int | None = None
    user_auth_headers: dict | None = None

    @pytest.fixture(autouse=True)
    def setup_and_teardown(self, client: TestClient, admin_user: dict):
        """Setup: create a regular user. Teardown: delete it."""
        # Create a regular user via admin
        response = client.post(
            "/users/",
            json={
                "email": "rbactest@example.com",
                "name": "RBAC Test User",
                "password": "securepassword123",
                "is_active": True,
            },
            headers=admin_user["headers"],
        )
        if response.status_code == 201:
            TestRBAC.created_user_id = response.json()["id"]
            TestRBAC.user_auth_headers = get_auth_headers(
                client,
                "rbactest@example.com",
                "securepassword123"
            )

        yield

        # Teardown
        if TestRBAC.created_user_id is not None:
            client.delete(
                f"/users/{TestRBAC.created_user_id}",
                headers=admin_user["headers"]
            )
            TestRBAC.created_user_id = None
            TestRBAC.user_auth_headers = None

    def test_create_user_as_regular_user_forbidden(self, client: TestClient):
        """Test that a regular user cannot create users (403)."""
        response = client.post(
            "/users/",
            json={
                "email": "shouldfail@example.com",
                "name": "Should Fail",
                "password": "securepassword123",
                "is_active": True,
            },
            headers=TestRBAC.user_auth_headers,
        )

        assert response.status_code == 403
        data = response.json()
        assert data["error_code"] == "INSUFFICIENT_ROLE"

    def test_create_user_as_admin_allowed(self, client: TestClient, admin_user: dict):
        """Test that an admin can create users (201)."""
        response = client.post(
            "/users/",
            json={
                "email": "admincanmake@example.com",
                "name": "Admin Created",
                "password": "securepassword123",
                "is_active": True,
            },
            headers=admin_user["headers"],
        )

        assert response.status_code == 201
        data = response.json()
        assert data["email"] == "admincanmake@example.com"

        # Clean up
        client.delete(
            f"/users/{data['id']}",
            headers=admin_user["headers"]
        )

    def test_list_users_as_regular_user_allowed(self, client: TestClient):
        """Test that a regular user can list users."""
        response = client.get("/users/", headers=TestRBAC.user_auth_headers)
        assert response.status_code == 200

    def test_get_user_as_regular_user_allowed(self, client: TestClient):
        """Test that a regular user can get a user by ID."""
        response = client.get(
            f"/users/{TestRBAC.created_user_id}",
            headers=TestRBAC.user_auth_headers
        )
        assert response.status_code == 200

    def test_update_user_as_regular_user_allowed(self, client: TestClient):
        """Test that a regular user can update a user."""
        response = client.put(
            f"/users/{TestRBAC.created_user_id}",
            json={"name": "Updated by Regular"},
            headers=TestRBAC.user_auth_headers
        )
        assert response.status_code == 200

    def test_delete_user_as_regular_user_allowed(self, client: TestClient, admin_user: dict):
        """Test that a regular user can delete (auth required, not role-specific)."""
        # Create a throwaway user to delete
        response = client.post(
            "/users/",
            json={
                "email": "deleteme@example.com",
                "name": "Delete Me",
                "password": "securepassword123",
                "is_active": True,
            },
            headers=admin_user["headers"],
        )
        assert response.status_code == 201
        throwaway_id = response.json()["id"]

        # Regular user deletes the throwaway user
        response = client.delete(
            f"/users/{throwaway_id}",
            headers=TestRBAC.user_auth_headers
        )
        assert response.status_code == 204

    def test_create_user_without_auth_returns_401(self, client: TestClient):
        """Test that creating a user without auth returns 401/403."""
        response = client.post(
            "/users/",
            json={
                "email": "noauth@example.com",
                "name": "No Auth",
                "password": "securepassword123",
                "is_active": True,
            },
        )
        # HTTPBearer returns 401 or 403 when no token provided
        assert response.status_code in [401, 403]


class TestProtectedRoutes:
    """Test that protected routes require authentication."""

    def test_list_users_without_auth(self, client: TestClient):
        """Test listing users without auth returns 401."""
        response = client.get("/users/")

        # HTTPBearer returns 401/403 depending on the issue
        assert response.status_code in [401, 403]

    def test_get_user_without_auth(self, client: TestClient):
        """Test getting a user without auth returns 401."""
        response = client.get("/users/1")

        assert response.status_code in [401, 403]

    def test_update_user_without_auth(self, client: TestClient):
        """Test updating a user without auth returns 401."""
        response = client.put("/users/1", json={"name": "Test"})

        assert response.status_code in [401, 403]

    def test_delete_user_without_auth(self, client: TestClient):
        """Test deleting a user without auth returns 401."""
        response = client.delete("/users/1")

        assert response.status_code in [401, 403]

    def test_create_user_without_auth(self, client: TestClient):
        """Test that creating a user without auth returns 401/403 (admin only)."""
        response = client.post("/users/", json={
            "email": "noauthrequired@example.com",
            "name": "No Auth User",
            "password": "securepassword123",
            "is_active": True,
        })

        # Now requires admin auth
        assert response.status_code in [401, 403]

    def test_list_users_with_invalid_token(self, client: TestClient):
        """Test listing users with invalid token returns 401."""
        response = client.get(
            "/users/",
            headers={"Authorization": "Bearer invalid_token"}
        )

        assert response.status_code == 401
        data = response.json()
        assert data["error_code"] == "INVALID_TOKEN"

    def test_list_users_with_malformed_header(self, client: TestClient):
        """Test listing users with malformed auth header returns 401."""
        response = client.get(
            "/users/",
            headers={"Authorization": "NotBearer token"}
        )

        assert response.status_code in [401, 403]
