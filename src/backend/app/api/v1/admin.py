"""Admin API endpoints for managing all models."""

from datetime import datetime
from uuid import UUID

from app.core.auth import require_admin
from app.core.exceptions import BadRequestException, NotFoundException
from app.core.logging import logger
from app.db.tables import (
    Answer,
    ConversationMessage,
    ConversationSession,
    DailyStudyPlan,
    Exam,
    ExamAttempt,
    MockExamSession,
    PlacementResponse,
    PlacementTest,
    ProgressSnapshot,
    Question,
    StudyActivity,
    User,
    UserRole,
)
from app.schemas.base import BaseSchema
from app.services.user import UserService
from litestar import Controller, Request, delete, get, patch, post
from litestar.status_codes import HTTP_200_OK, HTTP_201_CREATED, HTTP_204_NO_CONTENT
from pydantic import Field


# ─────────────────────────────────────────────────────────────────
# Admin Schemas
# ─────────────────────────────────────────────────────────────────


class PaginatedResponse(BaseSchema):
    """Paginated response wrapper."""
    items: list[dict]
    total: int
    page: int
    page_size: int
    total_pages: int


class AdminStatsResponse(BaseSchema):
    """Admin dashboard statistics."""
    total_users: int
    active_users: int
    admin_users: int
    total_exams: int
    total_questions: int
    total_attempts: int
    total_conversations: int


class ModelInfo(BaseSchema):
    """Information about a model."""
    name: str
    display_name: str
    description: str
    fields: list[dict]
    count: int


class AdminUserCreate(BaseSchema):
    """Schema for admin creating a user."""
    email: str
    password: str = Field(min_length=8)
    full_name: str
    role: str = "user"
    is_active: bool = True
    is_verified: bool = False


class AdminUserUpdate(BaseSchema):
    """Schema for admin updating a user."""
    email: str | None = None
    full_name: str | None = None
    role: str | None = None
    is_active: bool | None = None
    is_verified: bool | None = None
    target_exam: str | None = None
    target_score: float | None = None
    timezone: str | None = None


# ─────────────────────────────────────────────────────────────────
# Model Registry for Dynamic Admin
# ─────────────────────────────────────────────────────────────────

# Registry of all models available in admin
MODEL_REGISTRY = {
    "users": {
        "model": User,
        "display_name": "Users",
        "description": "User accounts",
        "searchable_fields": ["email", "full_name"],
        "editable_fields": ["email", "full_name", "role", "is_active", "is_verified", "target_exam", "target_score", "timezone"],
    },
    "exams": {
        "model": Exam,
        "display_name": "Exams",
        "description": "Exam definitions",
        "searchable_fields": ["title", "exam_type", "section"],
        "editable_fields": ["title", "description", "exam_type", "section", "duration_minutes", "total_questions", "difficulty_level", "is_active", "is_free"],
    },
    "questions": {
        "model": Question,
        "display_name": "Questions",
        "description": "Question bank",
        "searchable_fields": ["question_text", "question_type"],
        "editable_fields": ["question_text", "question_type", "options", "correct_answer", "explanation", "points"],
    },
    "exam_attempts": {
        "model": ExamAttempt,
        "display_name": "Exam Attempts",
        "description": "User exam attempts",
        "searchable_fields": ["status"],
        "editable_fields": ["score", "band_score", "status", "feedback"],
    },
    "answers": {
        "model": Answer,
        "display_name": "Answers",
        "description": "User answers to questions",
        "searchable_fields": [],
        "editable_fields": ["is_correct", "points_earned", "ai_feedback"],
    },
    "conversation_sessions": {
        "model": ConversationSession,
        "display_name": "Conversation Sessions",
        "description": "Conversation practice sessions",
        "searchable_fields": ["topic"],
        "editable_fields": ["topic", "scenario", "difficulty_level"],
    },
    "conversation_messages": {
        "model": ConversationMessage,
        "display_name": "Conversation Messages",
        "description": "Messages in conversations",
        "searchable_fields": ["content", "role"],
        "editable_fields": ["content", "role"],
    },
    "placement_tests": {
        "model": PlacementTest,
        "display_name": "Placement Tests",
        "description": "Initial diagnostic tests",
        "searchable_fields": ["status"],
        "editable_fields": ["status", "overall_band", "listening_band", "reading_band", "writing_band", "speaking_band"],
    },
    "placement_responses": {
        "model": PlacementResponse,
        "display_name": "Placement Responses",
        "description": "Responses in placement tests",
        "searchable_fields": ["section", "question_type"],
        "editable_fields": ["band_score", "ai_evaluation"],
    },
    "daily_study_plans": {
        "model": DailyStudyPlan,
        "display_name": "Daily Study Plans",
        "description": "AI-generated daily plans",
        "searchable_fields": [],
        "editable_fields": ["activities", "is_completed"],
    },
    "study_activities": {
        "model": StudyActivity,
        "display_name": "Study Activities",
        "description": "Individual study activities",
        "searchable_fields": ["title", "section", "activity_type"],
        "editable_fields": ["title", "section", "activity_type", "difficulty_level", "is_completed", "band_score"],
    },
    "progress_snapshots": {
        "model": ProgressSnapshot,
        "display_name": "Progress Snapshots",
        "description": "User progress snapshots",
        "searchable_fields": [],
        "editable_fields": ["overall_band", "listening_band", "reading_band", "writing_band", "speaking_band"],
    },
    "mock_exam_sessions": {
        "model": MockExamSession,
        "display_name": "Mock Exam Sessions",
        "description": "AI-powered mock exams",
        "searchable_fields": ["status", "section"],
        "editable_fields": ["status", "section", "band_score", "difficulty", "target_band"],
    },
}


def get_model_fields(model) -> list[dict]:
    """Get field information for a model."""
    fields = []
    for col in model._meta.columns:
        field_info = {
            "name": col._meta.name,
            "type": col.__class__.__name__,
            "nullable": col._meta.null,
            "primary_key": col._meta.primary_key,
        }
        if hasattr(col._meta, "default") and col._meta.default is not None:
            default = col._meta.default
            if callable(default):
                field_info["default"] = str(default)
            else:
                field_info["default"] = str(default)
        fields.append(field_info)
    return fields


def serialize_row(row: dict) -> dict:
    """Serialize a database row to JSON-safe dict."""
    result = {}
    for key, value in row.items():
        if isinstance(value, UUID):
            result[key] = str(value)
        elif isinstance(value, datetime) or hasattr(value, "isoformat"):
            result[key] = value.isoformat()
        else:
            result[key] = value
    return result


class AdminController(Controller):
    """Admin management controller."""

    path = "/admin"
    tags = ["Admin"]
    guards = [require_admin]

    # ─────────────────────────────────────────────────────────────
    # Dashboard & Stats
    # ─────────────────────────────────────────────────────────────

    @get(
        "/stats",
        summary="Get Admin Stats",
        description="Get dashboard statistics for admin.",
        status_code=HTTP_200_OK,
    )
    async def get_stats(self) -> AdminStatsResponse:
        """Get admin dashboard statistics."""
        total_users = await User.count()
        active_users = await User.count().where(User.is_active.eq(True))
        admin_users = await User.count().where(User.role == UserRole.ADMIN.value)
        total_exams = await Exam.count()
        total_questions = await Question.count()
        total_attempts = await ExamAttempt.count()
        total_conversations = await ConversationSession.count()

        return AdminStatsResponse(
            total_users=total_users,
            active_users=active_users,
            admin_users=admin_users,
            total_exams=total_exams,
            total_questions=total_questions,
            total_attempts=total_attempts,
            total_conversations=total_conversations,
        )

    # ─────────────────────────────────────────────────────────────
    # Model Discovery
    # ─────────────────────────────────────────────────────────────

    @get(
        "/models",
        summary="List All Models",
        description="Get a list of all available models for admin.",
        status_code=HTTP_200_OK,
    )
    async def list_models(self) -> list[ModelInfo]:
        """List all available models."""
        models = []
        for key, config in MODEL_REGISTRY.items():
            model = config["model"]
            count = await model.count()
            models.append(ModelInfo(
                name=key,
                display_name=config["display_name"],
                description=config["description"],
                fields=get_model_fields(model),
                count=count,
            ))
        return models

    @get(
        "/models/{model_name:str}",
        summary="Get Model Info",
        description="Get detailed information about a specific model.",
        status_code=HTTP_200_OK,
    )
    async def get_model_info(self, model_name: str) -> ModelInfo:
        """Get information about a specific model."""
        if model_name not in MODEL_REGISTRY:
            raise NotFoundException(detail=f"Model '{model_name}' not found")
        
        config = MODEL_REGISTRY[model_name]
        model = config["model"]
        count = await model.count()
        
        return ModelInfo(
            name=model_name,
            display_name=config["display_name"],
            description=config["description"],
            fields=get_model_fields(model),
            count=count,
        )

    # ─────────────────────────────────────────────────────────────
    # Generic CRUD Operations
    # ─────────────────────────────────────────────────────────────

    @get(
        "/models/{model_name:str}/records",
        summary="List Model Records",
        description="List records for a model with pagination and filtering.",
        status_code=HTTP_200_OK,
    )
    async def list_records(
        self,
        model_name: str,
        page: int = 1,
        page_size: int = 20,
        search: str | None = None,
        order_by: str = "created_at",
        order_dir: str = "desc",
    ) -> PaginatedResponse:
        """List records for a model."""
        if model_name not in MODEL_REGISTRY:
            raise NotFoundException(detail=f"Model '{model_name}' not found")
        
        config = MODEL_REGISTRY[model_name]
        model = config["model"]
        
        # Build query
        query = model.select()
        count_query = model.count()
        
        # Apply search if provided
        if search and config.get("searchable_fields"):
            search_conditions = []
            for field in config["searchable_fields"]:
                if hasattr(model, field):
                    col = getattr(model, field)
                    search_conditions.append(col.ilike(f"%{search}%"))
            
            if search_conditions:
                combined = search_conditions[0]
                for cond in search_conditions[1:]:
                    combined = combined | cond
                query = query.where(combined)
                count_query = count_query.where(combined)
        
        # Get total count
        total = await count_query
        
        # Apply ordering
        if hasattr(model, order_by):
            order_col = getattr(model, order_by)
            if order_dir.lower() == "desc":
                query = query.order_by(order_col, ascending=False)
            else:
                query = query.order_by(order_col, ascending=True)
        
        # Apply pagination
        offset = (page - 1) * page_size
        query = query.offset(offset).limit(page_size)
        
        # Execute query
        results = await query
        
        # Serialize results
        items = [serialize_row(dict(row)) for row in results]
        
        total_pages = (total + page_size - 1) // page_size if total > 0 else 1
        
        return PaginatedResponse(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )

    @get(
        "/models/{model_name:str}/records/{record_id:uuid}",
        summary="Get Record",
        description="Get a single record by ID.",
        status_code=HTTP_200_OK,
    )
    async def get_record(self, model_name: str, record_id: UUID) -> dict:
        """Get a single record."""
        if model_name not in MODEL_REGISTRY:
            raise NotFoundException(detail=f"Model '{model_name}' not found")
        
        config = MODEL_REGISTRY[model_name]
        model = config["model"]
        
        record = await model.select().where(model.id == record_id).first()
        if not record:
            raise NotFoundException(detail="Record not found")
        
        return serialize_row(dict(record))

    @patch(
        "/models/{model_name:str}/records/{record_id:uuid}",
        summary="Update Record",
        description="Update a record's fields.",
        status_code=HTTP_200_OK,
    )
    async def update_record(
        self,
        model_name: str,
        record_id: UUID,
        data: dict,
    ) -> dict:
        """Update a record."""
        if model_name not in MODEL_REGISTRY:
            raise NotFoundException(detail=f"Model '{model_name}' not found")
        
        config = MODEL_REGISTRY[model_name]
        model = config["model"]
        editable_fields = config.get("editable_fields", [])
        
        # Check record exists
        record = await model.select().where(model.id == record_id).first()
        if not record:
            raise NotFoundException(detail="Record not found")
        
        # Filter to only allowed fields
        update_data = {}
        for key, value in data.items():
            if key in editable_fields and hasattr(model, key):
                update_data[key] = value
        
        if not update_data:
            raise BadRequestException(detail="No valid fields to update")
        
        # Update
        await model.update(update_data).where(model.id == record_id)
        
        # Return updated record
        updated = await model.select().where(model.id == record_id).first()
        logger.info(f"Admin updated {model_name} record {record_id}")
        
        return serialize_row(dict(updated))

    @delete(
        "/models/{model_name:str}/records/{record_id:uuid}",
        summary="Delete Record",
        description="Delete a record by ID.",
        status_code=HTTP_204_NO_CONTENT,
    )
    async def delete_record(self, model_name: str, record_id: UUID) -> None:
        """Delete a record."""
        if model_name not in MODEL_REGISTRY:
            raise NotFoundException(detail=f"Model '{model_name}' not found")
        
        config = MODEL_REGISTRY[model_name]
        model = config["model"]
        
        # Check record exists
        record = await model.select().where(model.id == record_id).first()
        if not record:
            raise NotFoundException(detail="Record not found")
        
        await model.delete().where(model.id == record_id)
        logger.info(f"Admin deleted {model_name} record {record_id}")

    # ─────────────────────────────────────────────────────────────
    # User-Specific Admin Operations
    # ─────────────────────────────────────────────────────────────

    @get(
        "/users",
        summary="List Users",
        description="List all users with pagination.",
        status_code=HTTP_200_OK,
    )
    async def list_users(
        self,
        page: int = 1,
        page_size: int = 20,
        search: str | None = None,
        role: str | None = None,
        is_active: bool | None = None,
    ) -> PaginatedResponse:
        """List all users."""
        query = User.select()
        count_query = User.count()
        
        # Apply filters
        if search:
            query = query.where(
                (User.email.ilike(f"%{search}%")) | (User.full_name.ilike(f"%{search}%"))
            )
            count_query = count_query.where(
                (User.email.ilike(f"%{search}%")) | (User.full_name.ilike(f"%{search}%"))
            )
        
        if role:
            query = query.where(User.role == role)
            count_query = count_query.where(User.role == role)
        
        if is_active is not None:
            query = query.where(User.is_active == is_active)
            count_query = count_query.where(User.is_active == is_active)
        
        total = await count_query
        
        offset = (page - 1) * page_size
        results = await query.order_by(User.created_at, ascending=False).offset(offset).limit(page_size)
        
        items = [serialize_row(dict(row)) for row in results]
        # Remove password_hash from response
        for item in items:
            item.pop("password_hash", None)
        
        total_pages = (total + page_size - 1) // page_size if total > 0 else 1
        
        return PaginatedResponse(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )

    @post(
        "/users",
        summary="Create User",
        description="Create a new user (admin can set role).",
        status_code=HTTP_201_CREATED,
    )
    async def create_user(self, data: AdminUserCreate) -> dict:
        """Create a new user as admin."""
        from uuid import uuid4
        
        # Check if email exists
        existing = await User.select().where(User.email == data.email.lower()).first()
        if existing:
            raise BadRequestException(detail="Email already registered")
        
        user_service = UserService()
        user_data = {
            "id": uuid4(),
            "email": data.email.lower(),
            "password_hash": user_service.hash_password(data.password),
            "full_name": data.full_name,
            "role": data.role,
            "is_active": data.is_active,
            "is_verified": data.is_verified,
        }
        
        user = User(**user_data)
        await user.save()
        
        logger.info(f"Admin created user {data.email}")
        
        result = await User.select().where(User.id == user_data["id"]).first()
        serialized = serialize_row(dict(result))
        serialized.pop("password_hash", None)
        
        return serialized

    @patch(
        "/users/{user_id:uuid}",
        summary="Update User",
        description="Update user information including role.",
        status_code=HTTP_200_OK,
    )
    async def update_user(self, user_id: UUID, data: AdminUserUpdate) -> dict:
        """Update a user as admin."""
        user = await User.select().where(User.id == user_id).first()
        if not user:
            raise NotFoundException(detail="User not found")
        
        update_data = {k: v for k, v in data.model_dump().items() if v is not None}
        
        if "email" in update_data:
            update_data["email"] = update_data["email"].lower()
            # Check email not taken
            existing = await User.select().where(
                (User.email == update_data["email"]) & (User.id != user_id)
            ).first()
            if existing:
                raise BadRequestException(detail="Email already taken")
        
        if update_data:
            await User.update(update_data).where(User.id == user_id)
        
        updated = await User.select().where(User.id == user_id).first()
        logger.info(f"Admin updated user {user_id}")
        
        serialized = serialize_row(dict(updated))
        serialized.pop("password_hash", None)
        
        return serialized

    @delete(
        "/users/{user_id:uuid}",
        summary="Delete User",
        description="Delete a user account.",
        status_code=HTTP_204_NO_CONTENT,
    )
    async def delete_user(self, user_id: UUID, request: Request) -> None:
        """Delete a user."""
        # Prevent self-deletion
        if request.state.user_id == user_id:
            raise BadRequestException(detail="Cannot delete your own account")
        
        user = await User.select().where(User.id == user_id).first()
        if not user:
            raise NotFoundException(detail="User not found")
        
        await User.delete().where(User.id == user_id)
        logger.info(f"Admin deleted user {user_id}")

    @post(
        "/users/{user_id:uuid}/reset-password",
        summary="Reset User Password",
        description="Reset a user's password.",
        status_code=HTTP_200_OK,
    )
    async def reset_password(self, user_id: UUID, data: dict) -> dict:
        """Reset a user's password."""
        user = await User.select().where(User.id == user_id).first()
        if not user:
            raise NotFoundException(detail="User not found")
        
        new_password = data.get("password")
        if not new_password or len(new_password) < 8:
            raise BadRequestException(detail="Password must be at least 8 characters")
        
        user_service = UserService()
        password_hash = user_service.hash_password(new_password)
        
        await User.update({"password_hash": password_hash}).where(User.id == user_id)
        logger.info(f"Admin reset password for user {user_id}")
        
        return {"message": "Password reset successfully"}
