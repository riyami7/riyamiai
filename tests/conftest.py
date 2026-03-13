"""Pytest configuration and fixtures."""

import uuid
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.db import get_db
from app.models.user import User
from app.utils.security import hash_password


# Admin credentials used across tests
ADMIN_EMAIL = "admin@testsetup.com"
ADMIN_PASSWORD = "adminpassword123"


@pytest.fixture(scope="module")
def client() -> TestClient:
    """Create a test client for the FastAPI application."""
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture(scope="module")
def admin_user(client: TestClient) -> dict:
    """Create an admin user directly in the database for testing.

    This fixture creates the admin once per test module and returns
    a dict with user info and auth headers.
    """
    # Create admin directly in the database (bypassing API which requires admin)
    db: Session = next(get_db())
    try:
        # Check if admin already exists
        existing = db.query(User).filter(User.email == ADMIN_EMAIL).first()
        if existing:
            # Clean up stale admin from previous test run
            db.delete(existing)
            db.commit()

        admin = User(
            email=ADMIN_EMAIL,
            name="Test Admin",
            hashed_password=hash_password(ADMIN_PASSWORD),
            role="admin",
            is_active=True,
        )
        db.add(admin)
        db.commit()
        db.refresh(admin)
        admin_id = admin.id
    finally:
        db.close()

    # Get auth token via login
    login_response = client.post("/auth/login", json={
        "email": ADMIN_EMAIL,
        "password": ADMIN_PASSWORD,
    })
    assert login_response.status_code == 200
    token = login_response.json()["access_token"]

    yield {
        "id": admin_id,
        "email": ADMIN_EMAIL,
        "password": ADMIN_PASSWORD,
        "headers": {"Authorization": f"Bearer {token}"},
    }

    # Teardown - delete admin user
    db = next(get_db())
    try:
        admin = db.query(User).filter(User.id == admin_id).first()
        if admin:
            db.delete(admin)
            db.commit()
    finally:
        db.close()


@pytest.fixture
def test_user_data() -> dict:
    """Sample user data for testing with unique email."""
    unique_id = uuid.uuid4().hex[:8]
    return {
        "email": f"testuser_{unique_id}@example.com",
        "name": "Test User",
        "password": "securepassword123",
        "is_active": True,
    }


@pytest.fixture
def test_user_update_data() -> dict:
    """Sample user update data for testing."""
    return {
        "name": "Updated Test User",
        "is_active": True,  # Keep user active for subsequent tests
    }
