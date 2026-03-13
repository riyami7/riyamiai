"""Authentication service layer for login and token management."""

from sqlalchemy.orm import Session

from app.repositories.user import UserRepository
from app.schemas.auth import LoginRequest, TokenResponse
from app.utils.security import verify_password, create_access_token
from app.exceptions import UnauthorizedError


class AuthService:
    """Service class for authentication-related business logic."""

    def __init__(self, db: Session):
        self.user_repository = UserRepository(db)

    def authenticate(self, credentials: LoginRequest) -> TokenResponse:
        """Authenticate a user and return an access token.

        Args:
            credentials: Login credentials (email and password).

        Returns:
            TokenResponse with access token.

        Raises:
            UnauthorizedError: If credentials are invalid.
        """
        # Find user by email
        user = self.user_repository.get_by_email(credentials.email)

        if user is None:
            raise UnauthorizedError(
                detail="Invalid email or password",
                error_code="INVALID_CREDENTIALS",
            )

        # Verify password
        if not verify_password(credentials.password, user.hashed_password):
            raise UnauthorizedError(
                detail="Invalid email or password",
                error_code="INVALID_CREDENTIALS",
            )

        # Check if user is active
        if not user.is_active:
            raise UnauthorizedError(
                detail="User account is disabled",
                error_code="USER_DISABLED",
            )

        # Create access token with role
        access_token = create_access_token(subject=user.id, role=user.role)

        return TokenResponse(
            access_token=access_token,
            token_type="bearer",
        )
