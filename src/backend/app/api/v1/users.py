"""User API endpoints."""

import json
from uuid import UUID

from app.core.auth import (
    ACCESS_TOKEN_EXPIRE_MINUTES,
    create_access_token,
    create_refresh_token,
    decode_token,
    extract_token_from_header,
    get_user_id_from_token,
    require_auth,
)
from app.db.tables import User
from app.schemas.user import (
    AuthResponse,
    TokenResponse,
    UserCreate,
    UserLogin,
    UserResponse,
    UserSettingsResponse,
    UserSettingsUpdate,
    UserUpdate,
)
from app.services.user import user_service
from litestar import Controller, Request, get, post, put
from litestar.status_codes import HTTP_200_OK, HTTP_201_CREATED


def _mask_key(key: str) -> str:
    """Mask an API key for safe display: show first 4 and last 4 chars."""
    if len(key) <= 10:
        return key[:2] + "***" + key[-2:]
    return key[:4] + "***" + key[-4:]


def _normalize_skill_profile(value: object) -> dict:
    """Return a safe dict for user responses."""
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except json.JSONDecodeError:
            return {}
    return value if isinstance(value, dict) else {}


def _user_to_response(user: dict) -> UserResponse:
    """Convert a user dict (from Piccolo) to UserResponse."""
    return UserResponse(
        id=user["id"],
        email=user["email"],
        full_name=user["full_name"],
        avatar_url=user.get("avatar_url"),
        is_active=user["is_active"],
        is_verified=user["is_verified"],
        target_exam=user.get("target_exam"),
        target_score=user.get("target_score"),
        timezone=user.get("timezone", "UTC"),
        preferences=user.get("preferences") or {},
        created_at=user.get("created_at"),
        updated_at=user.get("updated_at"),
        last_login_at=user.get("last_login_at"),
        target_band_score=user.get("target_band_score"),
        exam_date=user.get("exam_date"),
        preferred_daily_practice_time=user.get("preferred_daily_practice_time"),
        current_estimated_band=user.get("current_estimated_band"),
        skill_profile=_normalize_skill_profile(user.get("skill_profile")),
        section_scores=user.get("section_scores") or {},
        onboarding_completed=user.get("onboarding_completed", False),
    )


class UserController(Controller):
    """User management controller."""

    path = "/users"
    tags = ["Users"]

    @post(
        "/register",
        summary="Register User",
        description="Register a new user account and return auth tokens.",
        status_code=HTTP_201_CREATED,
    )
    async def register(self, data: UserCreate) -> AuthResponse:
        """Register a new user."""
        user = await user_service.create_user(data)

        # Fetch as dict so we can build the response uniformly
        user_dict = await user_service.get_by_email(data.email)
        user_resp = _user_to_response(user_dict)

        access_token = create_access_token(user_resp.id, user_resp.email)
        refresh_token = create_refresh_token(user_resp.id)

        return AuthResponse(
            user=user_resp,
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        )

    @post(
        "/login",
        summary="Login",
        description="Authenticate user and get access token.",
        status_code=HTTP_200_OK,
    )
    async def login(self, data: UserLogin) -> AuthResponse:
        """Authenticate user."""
        user = await user_service.authenticate(data.email, data.password)
        user_resp = _user_to_response(user)

        access_token = create_access_token(user_resp.id, user_resp.email)
        refresh_token = create_refresh_token(user_resp.id)

        return AuthResponse(
            user=user_resp,
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        )

    @post(
        "/refresh",
        summary="Refresh Token",
        description="Get a new access token using a refresh token.",
        status_code=HTTP_200_OK,
    )
    async def refresh_token(self, request: Request) -> TokenResponse:
        """Refresh access token."""
        authorization = request.headers.get("authorization")
        token = extract_token_from_header(authorization)
        payload = decode_token(token)

        if payload.get("type") != "refresh":
            from app.core.exceptions import UnauthorizedException

            raise UnauthorizedException(detail="Invalid token type")

        user_id = UUID(payload["sub"])
        user = await user_service.get_by_id(user_id)
        if not user:
            from app.core.exceptions import UnauthorizedException

            raise UnauthorizedException(detail="User not found")

        new_access = create_access_token(user_id, user["email"])
        new_refresh = create_refresh_token(user_id)

        return TokenResponse(
            access_token=new_access,
            refresh_token=new_refresh,
            token_type="bearer",
            expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        )

    @get(
        "/me",
        summary="Get Current User",
        description="Get the currently authenticated user's information.",
        status_code=HTTP_200_OK,
        guards=[require_auth],
    )
    async def get_me(self, request: Request) -> UserResponse:
        """Get current authenticated user."""
        user_id: UUID = request.state.user_id
        user = await user_service.get_by_id(user_id)
        if not user:
            from app.core.exceptions import NotFoundException

            raise NotFoundException(detail="User not found")
        return _user_to_response(user)

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
        return _user_to_response(user)

    @put(
        "/{user_id:uuid}",
        summary="Update User",
        description="Update user information.",
        status_code=HTTP_200_OK,
        guards=[require_auth],
    )
    async def update_user(self, user_id: UUID, data: UserUpdate) -> UserResponse:
        """Update user."""
        user = await user_service.update_user(user_id, data)
        return _user_to_response(user)

    @get(
        "/{user_id:uuid}/stats",
        summary="Get User Stats",
        description="Get user statistics including exam attempts and conversation sessions.",
        status_code=HTTP_200_OK,
    )
    async def get_user_stats(self, user_id: UUID) -> dict:
        """Get user statistics."""
        return await user_service.get_user_stats(user_id)

    # ── User Settings (API keys) ─────────────────────────────

    @get(
        "/me/settings",
        summary="Get User Settings",
        description="Get the current user's settings including masked API keys.",
        status_code=HTTP_200_OK,
        guards=[require_auth],
    )
    async def get_settings(self, request: Request) -> UserSettingsResponse:
        """Return user settings with masked API keys."""
        user_id: UUID = request.state.user_id
        user = await user_service.get_by_id(user_id)
        if not user:
            from app.core.exceptions import NotFoundException
            raise NotFoundException(detail="User not found")

        prefs = user.get("preferences") or {}
        if isinstance(prefs, str):
            try:
                prefs = json.loads(prefs)
            except json.JSONDecodeError:
                prefs = {}

        raw_keys: list[str] = prefs.get("gemini_api_keys", [])
        masked = [_mask_key(k) for k in raw_keys]

        return UserSettingsResponse(
            gemini_api_keys=masked,
            has_gemini_keys=len(raw_keys) > 0,
        )

    @put(
        "/me/settings",
        summary="Update User Settings",
        description="Update API keys and other settings.",
        status_code=HTTP_200_OK,
        guards=[require_auth],
    )
    async def update_settings(
        self, request: Request, data: UserSettingsUpdate
    ) -> UserSettingsResponse:
        """Save user-level API keys into the preferences JSON column."""
        user_id: UUID = request.state.user_id
        user = await user_service.get_by_id(user_id)
        if not user:
            from app.core.exceptions import NotFoundException
            raise NotFoundException(detail="User not found")

        prefs = user.get("preferences") or {}
        if isinstance(prefs, str):
            try:
                prefs = json.loads(prefs)
            except json.JSONDecodeError:
                prefs = {}

        prefs = dict(prefs)

        if data.gemini_api_keys is not None:
            # Filter out empty strings
            clean_keys = [k.strip() for k in data.gemini_api_keys if k.strip()]
            prefs["gemini_api_keys"] = clean_keys

        await User.update({"preferences": prefs}).where(User.id == user_id)

        masked = [_mask_key(k) for k in prefs.get("gemini_api_keys", [])]
        return UserSettingsResponse(
            gemini_api_keys=masked,
            has_gemini_keys=len(masked) > 0,
        )
