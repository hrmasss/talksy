"""User API endpoints."""

from uuid import UUID

from litestar import Controller, get, post, put, delete
from litestar.status_codes import HTTP_200_OK, HTTP_201_CREATED, HTTP_204_NO_CONTENT

from app.schemas.user import (
    UserCreate,
    UserUpdate,
    UserResponse,
    UserLogin,
    TokenResponse,
)
from app.services.user import user_service


class UserController(Controller):
    """User management controller."""

    path = "/users"
    tags = ["Users"]

    @post(
        "/register",
        summary="Register User",
        description="Register a new user account.",
        status_code=HTTP_201_CREATED,
    )
    async def register(self, data: UserCreate) -> dict:
        """Register a new user."""
        from uuid import UUID as PyUUID
        from datetime import datetime
        
        user = await user_service.create_user(data)
        
        # Handle UUID conversion
        user_id = str(user.id)
        
        return {
            "id": user_id,
            "email": user.email,
            "full_name": user.full_name,
            "is_active": user.is_active,
            "is_admin": user.is_admin,
            "is_verified": user.is_verified,
            "target_exam": user.target_exam,
            "target_score": user.target_score,
            "timezone": user.timezone,
            "preferences": user.preferences or {},
            "created_at": str(user.created_at) if user.created_at else None,
            "updated_at": str(user.updated_at) if user.updated_at else None,
        }

    @post(
        "/login",
        summary="Login",
        description="Authenticate user and get access token.",
        status_code=HTTP_200_OK,
    )
    async def login(self, data: UserLogin) -> TokenResponse:
        """Authenticate user."""
        user = await user_service.authenticate(data.email, data.password)
        
        # Generate tokens (simplified - use JWT in production)
        import secrets
        access_token = secrets.token_urlsafe(32)
        refresh_token = secrets.token_urlsafe(32)
        
        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=3600,
        )

    @get(
        "/{user_id:uuid}",
        summary="Get User",
        description="Get user information by ID.",
        status_code=HTTP_200_OK,
    )
    async def get_user(self, user_id: UUID) -> UserResponse:
        """Get user by ID."""
        user = await user_service.get_by_id(user_id)
        if not user:
            from litestar.exceptions import NotFoundException
            raise NotFoundException(detail="User not found")
        
        return UserResponse(
            id=user["id"],
            email=user["email"],
            full_name=user["full_name"],
            avatar_url=user.get("avatar_url"),
            is_active=user["is_active"],
            is_admin=user["is_admin"],
            is_verified=user["is_verified"],
            target_exam=user.get("target_exam"),
            target_score=user.get("target_score"),
            timezone=user["timezone"],
            preferences=user.get("preferences", {}),
            created_at=user["created_at"],
            updated_at=user.get("updated_at"),
            last_login_at=user.get("last_login_at"),
        )

    @put(
        "/{user_id:uuid}",
        summary="Update User",
        description="Update user information.",
        status_code=HTTP_200_OK,
    )
    async def update_user(self, user_id: UUID, data: UserUpdate) -> UserResponse:
        """Update user."""
        user = await user_service.update_user(user_id, data)
        return UserResponse(
            id=user["id"],
            email=user["email"],
            full_name=user["full_name"],
            avatar_url=user.get("avatar_url"),
            is_active=user["is_active"],
            is_admin=user["is_admin"],
            is_verified=user["is_verified"],
            target_exam=user.get("target_exam"),
            target_score=user.get("target_score"),
            timezone=user["timezone"],
            preferences=user.get("preferences", {}),
            created_at=user["created_at"],
            updated_at=user.get("updated_at"),
        )

    @get(
        "/{user_id:uuid}/stats",
        summary="Get User Stats",
        description="Get user statistics including exam attempts and conversation sessions.",
        status_code=HTTP_200_OK,
    )
    async def get_user_stats(self, user_id: UUID) -> dict:
        """Get user statistics."""
        return await user_service.get_user_stats(user_id)
