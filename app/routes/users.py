"""User CRUD routes."""

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.schemas.user import (
    UserCreate,
    UserUpdate,
    UserResponse,
    UserListResponse,
)
from app.schemas.error import ErrorResponse
from app.db import get_db
from app.services.user import UserService
from app.models.user import User
from app.dependencies.auth import get_current_user, require_role

router = APIRouter(
    prefix="/users",
    tags=["Users"]
)


def get_user_service(db: Session = Depends(get_db)) -> UserService:
    """Dependency to get UserService instance."""
    return UserService(db)


@router.post(
    "/",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        403: {"model": ErrorResponse, "description": "Forbidden - admin role required"},
        409: {"model": ErrorResponse, "description": "Email already exists"},
    },
)
async def create_user(
    user: UserCreate,
    service: UserService = Depends(get_user_service),
    current_user: User = Depends(require_role("admin")),
) -> UserResponse:
    """Create a new user (admin only)."""
    db_user = service.create(user)
    return UserResponse.model_validate(db_user)


@router.get(
    "/",
    response_model=UserListResponse,
    responses={
        401: {"model": ErrorResponse, "description": "Unauthorized"},
    },
)
async def list_users(
    skip: int = 0,
    limit: int = 100,
    service: UserService = Depends(get_user_service),
    current_user: User = Depends(get_current_user),
) -> UserListResponse:
    """List all users with pagination (auth required)."""
    users, total = service.get_all(skip=skip, limit=limit)

    return UserListResponse(
        users=[UserResponse.model_validate(user) for user in users],
        total=total
    )


@router.get(
    "/{user_id}",
    response_model=UserResponse,
    responses={
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        404: {"model": ErrorResponse, "description": "User not found"},
    },
)
async def get_user(
    user_id: int,
    service: UserService = Depends(get_user_service),
    current_user: User = Depends(get_current_user),
) -> UserResponse:
    """Get a specific user by ID (auth required)."""
    user = service.get_by_id(user_id)
    return UserResponse.model_validate(user)


@router.put(
    "/{user_id}",
    response_model=UserResponse,
    responses={
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        404: {"model": ErrorResponse, "description": "User not found"},
        409: {"model": ErrorResponse, "description": "Email already exists"},
    },
)
async def update_user(
    user_id: int,
    user: UserUpdate,
    service: UserService = Depends(get_user_service),
    current_user: User = Depends(get_current_user),
) -> UserResponse:
    """Update an existing user (auth required)."""
    db_user = service.update(user_id, user)
    return UserResponse.model_validate(db_user)


@router.delete(
    "/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        404: {"model": ErrorResponse, "description": "User not found"},
    },
)
async def delete_user(
    user_id: int,
    service: UserService = Depends(get_user_service),
    current_user: User = Depends(get_current_user),
) -> None:
    """Delete a user by ID (auth required)."""
    service.delete(user_id)
