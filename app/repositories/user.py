"""User repository for data access operations."""

from sqlalchemy.orm import Session

from app.models.user import User


class UserRepository:
    """Repository class for user data access."""

    def __init__(self, db: Session):
        self.db = db

    def create(self, user: User) -> User:
        """Create a new user in the database.
        
        Args:
            user: User model instance to create.
            
        Returns:
            The created user with ID populated.
        """
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user

    def get_by_id(self, user_id: int) -> User | None:
        """Get a user by ID.
        
        Args:
            user_id: The user's ID.
            
        Returns:
            The user if found, None otherwise.
        """
        return self.db.query(User).filter(User.id == user_id).first()

    def get_by_email(self, email: str) -> User | None:
        """Get a user by email.
        
        Args:
            email: The user's email.
            
        Returns:
            The user if found, None otherwise.
        """
        return self.db.query(User).filter(User.email == email).first()

    def get_all(self, skip: int = 0, limit: int = 100) -> list[User]:
        """Get all users with pagination.
        
        Args:
            skip: Number of records to skip.
            limit: Maximum number of records to return.
            
        Returns:
            List of users.
        """
        return self.db.query(User).order_by(User.id).offset(skip).limit(limit).all()

    def count(self) -> int:
        """Get total count of users.
        
        Returns:
            Total number of users.
        """
        return self.db.query(User).count()

    def update(self, user: User) -> User:
        """Update a user in the database.
        
        Args:
            user: User model instance with updated fields.
            
        Returns:
            The updated user.
        """
        self.db.commit()
        self.db.refresh(user)
        return user

    def delete(self, user: User) -> None:
        """Delete a user from the database.
        
        Args:
            user: User model instance to delete.
        """
        self.db.delete(user)
        self.db.commit()
