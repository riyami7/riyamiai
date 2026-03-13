"""Authentication dependencies for route protection."""

from typing import Callable

from fastapi import Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.db import get_db
from app.models.user import User
from app.repositories.user import UserRepository
from app.utils.security import decode_access_token
from app.exceptions import UnauthorizedError, ForbiddenError

# HTTP Bearer scheme for extracting token from Authorization header
security = HTTPBearer()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
) -> User:
    """Extract and validate JWT token, return the current user.

    Args:
        credentials: HTTP Authorization credentials (Bearer token).
        db: Database session.

    Returns:
        The authenticated User object.

    Raises:
        UnauthorizedError: If token is missing, invalid, expired, or user not found.
    """
    token = credentials.credentials

    # Decode and validate token
    payload = decode_access_token(token)
    if payload is None:
        raise UnauthorizedError(
            detail="Invalid or expired token",
            error_code="INVALID_TOKEN",
        )

    # Extract user ID from token
    user_id = payload.get("sub")
    if user_id is None:
        raise UnauthorizedError(
            detail="Invalid token payload",
            error_code="INVALID_TOKEN",
        )

    # Get user from database
    user_repository = UserRepository(db)
    user = user_repository.get_by_id(int(user_id))

    if user is None:
        raise UnauthorizedError(
            detail="User not found",
            error_code="USER_NOT_FOUND",
        )

    if not user.is_active:
        raise UnauthorizedError(
            detail="User account is disabled",
            error_code="USER_DISABLED",
        )

    return user


def require_role(*allowed_roles: str) -> Callable:
    """Create a dependency that checks if the current user has an allowed role.

    Args:
        *allowed_roles: One or more role strings (e.g., "admin", "user").

    Returns:
        A FastAPI dependency function that validates the user's role.

    Example:
        @router.post("/", dependencies=[Depends(require_role("admin"))])
        async def admin_only_endpoint(...):
            ...
    """
    def role_checker(current_user: User = Depends(get_current_user)) -> User:
        """Verify the current user has one of the allowed roles.

        Args:
            current_user: The authenticated user from JWT.

        Returns:
            The authenticated user if role is allowed.

        Raises:
            ForbiddenError: If user's role is not in the allowed roles.
        """
        if current_user.role not in allowed_roles:
            raise ForbiddenError(
                detail="You do not have permission to perform this action",
                error_code="INSUFFICIENT_ROLE",
                context={
                    "user_role": current_user.role,
                    "required_roles": list(allowed_roles),
                },
            )
        return current_user

    return role_checker
