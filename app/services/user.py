"""User service layer for business logic."""

from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate
from app.repositories.user import UserRepository
from app.exceptions import NotFoundError, AlreadyExistsError, DatabaseError
from app.utils.security import hash_password


class UserService:
    """Service class for user-related business logic."""

    def __init__(self, db: Session):
        self.repository = UserRepository(db)

    def create(self, user_data: UserCreate) -> User:
        """Create a new user.
        
        Args:
            user_data: User creation data.
            
        Returns:
            The created user.
            
        Raises:
            AlreadyExistsError: If email is already registered.
        """
        # Check if email already exists
        existing_user = self.repository.get_by_email(user_data.email)
        if existing_user:
            raise AlreadyExistsError(
                detail="Email already registered",
                error_code="EMAIL_ALREADY_EXISTS",
                context={"email": user_data.email},
            )

        db_user = User(
            email=user_data.email,
            name=user_data.name,
            hashed_password=hash_password(user_data.password),
            role=user_data.role,
            is_active=user_data.is_active,
            system_prompt=user_data.system_prompt,
        )

        try:
            return self.repository.create(db_user)
        except IntegrityError as e:
            raise AlreadyExistsError(
                detail="Email already registered",
                error_code="EMAIL_ALREADY_EXISTS",
                context={"email": user_data.email},
            ) from e

    def get_by_id(self, user_id: int) -> User:
        """Get a user by ID.
        
        Args:
            user_id: The user's ID.
            
        Returns:
            The user.
            
        Raises:
            NotFoundError: If user is not found.
        """
        user = self.repository.get_by_id(user_id)

        if user is None:
            raise NotFoundError(
                detail="User not found",
                error_code="USER_NOT_FOUND",
                context={"user_id": user_id},
            )

        return user

    def get_all(self, skip: int = 0, limit: int = 100) -> tuple[list[User], int]:
        """Get all users with pagination.
        
        Args:
            skip: Number of records to skip.
            limit: Maximum number of records to return.
            
        Returns:
            Tuple of (users list, total count).
        """
        users = self.repository.get_all(skip=skip, limit=limit)
        total = self.repository.count()

        return users, total

    def update(self, user_id: int, user_data: UserUpdate) -> User:
        """Update an existing user.
        
        Args:
            user_id: The user's ID.
            user_data: User update data.
            
        Returns:
            The updated user.
            
        Raises:
            NotFoundError: If user is not found.
            AlreadyExistsError: If new email is already registered.
        """
        db_user = self.repository.get_by_id(user_id)

        if db_user is None:
            raise NotFoundError(
                detail="User not found",
                error_code="USER_NOT_FOUND",
                context={"user_id": user_id},
            )

        update_data = user_data.model_dump(exclude_unset=True)

        if not update_data:
            return db_user

        # Check if new email already exists (if email is being updated)
        if "email" in update_data and update_data["email"] != db_user.email:
            existing_user = self.repository.get_by_email(update_data["email"])
            if existing_user:
                raise AlreadyExistsError(
                    detail="Email already registered",
                    error_code="EMAIL_ALREADY_EXISTS",
                    context={"email": update_data["email"]},
                )

        try:
            for field, value in update_data.items():
                setattr(db_user, field, value)

            db_user.updated_at = datetime.now(timezone.utc)

            return self.repository.update(db_user)
        except IntegrityError as e:
            raise AlreadyExistsError(
                detail="Email already registered",
                error_code="EMAIL_ALREADY_EXISTS",
                context={"email": user_data.email},
            ) from e

    def delete(self, user_id: int) -> None:
        """Delete a user by ID.
        
        Args:
            user_id: The user's ID.
            
        Raises:
            NotFoundError: If user is not found.
        """
        db_user = self.repository.get_by_id(user_id)

        if db_user is None:
            raise NotFoundError(
                detail="User not found",
                error_code="USER_NOT_FOUND",
                context={"user_id": user_id},
            )

        self.repository.delete(db_user)
