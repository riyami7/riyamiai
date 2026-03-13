"""Script to create the first admin user.

Usage:
    python -m scripts.create_admin

This script creates an admin user directly in the database.
Run this once after initial setup to bootstrap the first admin,
since the POST /users/ endpoint now requires admin authentication.
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from getpass import getpass

from sqlalchemy.orm import Session

from app.db import get_db
from app.models.user import User
from app.utils.security import hash_password


def create_admin() -> None:
    """Create an admin user interactively."""
    print("=== Create Admin User ===\n")

    email = input("Email: ").strip()
    if not email:
        print("Error: Email is required.")
        sys.exit(1)

    name = input("Name: ").strip()
    if not name:
        print("Error: Name is required.")
        sys.exit(1)

    password = getpass("Password (min 8 chars): ")
    if len(password) < 8:
        print("Error: Password must be at least 8 characters.")
        sys.exit(1)

    password_confirm = getpass("Confirm password: ")
    if password != password_confirm:
        print("Error: Passwords do not match.")
        sys.exit(1)

    # Create admin in database
    db: Session = next(get_db())
    try:
        # Check if email already exists
        existing = db.query(User).filter(User.email == email).first()
        if existing:
            print(f"Error: User with email '{email}' already exists.")
            if existing.role != "admin":
                promote = input("Promote this user to admin? [y/N]: ").strip().lower()
                if promote == "y":
                    existing.role = "admin"
                    db.commit()
                    print(f"User '{email}' promoted to admin.")
                    return
            else:
                print("This user is already an admin.")
            sys.exit(1)

        admin = User(
            email=email,
            name=name,
            hashed_password=hash_password(password),
            role="admin",
            is_active=True,
        )
        db.add(admin)
        db.commit()
        db.refresh(admin)

        print(f"\nAdmin user created successfully!")
        print(f"  ID:    {admin.id}")
        print(f"  Email: {admin.email}")
        print(f"  Name:  {admin.name}")
        print(f"  Role:  {admin.role}")

    except Exception as e:
        db.rollback()
        print(f"Error creating admin: {e}")
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    create_admin()
