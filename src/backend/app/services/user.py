"""User service for user-related operations."""

import hashlib
import secrets
from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from app.core.exceptions import ConflictException, NotFoundException, UnauthorizedException
from app.core.logging import logger
from app.db.tables import User
from app.schemas.user import UserCreate, UserUpdate
from app.services.base import BaseService


class UserService(BaseService[User]):
    """Service for user operations."""

    model = User

    @staticmethod
    def hash_password(password: str) -> str:
        """Hash a password using SHA-256 with salt."""
        salt = secrets.token_hex(16)
        hashed = hashlib.sha256(f"{salt}{password}".encode()).hexdigest()
        return f"{salt}${hashed}"

    @staticmethod
    def verify_password(password: str, password_hash: str) -> bool:
        """Verify a password against its hash."""
        try:
            salt, hashed = password_hash.split("$")
            return hashlib.sha256(f"{salt}{password}".encode()).hexdigest() == hashed
        except ValueError:
            return False

    async def get_by_email(self, email: str) -> User | None:
        """Get user by email."""
        try:
            result = await User.select().where(User.email == email.lower()).first()
            return result
        except Exception as e:
            logger.error(f"Error fetching user by email {email}: {e}")
            return None

    async def create_user(self, data: UserCreate) -> User:
        """Create a new user."""
        # Check if email already exists
        existing = await self.get_by_email(data.email)
        if existing:
            raise ConflictException(detail="Email already registered")

        user_data = {
            "id": uuid4(),
            "email": data.email.lower(),
            "password_hash": self.hash_password(data.password),
            "full_name": data.full_name,
            "target_exam": data.target_exam,
            "target_score": data.target_score,
            "timezone": data.timezone,
            "is_active": True,
            "is_verified": False,
        }

        user = User(**user_data)
        await user.save()
        logger.info(f"Created user with email {data.email}")
        return user

    async def update_user(self, user_id: UUID, data: UserUpdate) -> User:
        """Update user information."""
        user = await self.get_by_id(user_id)
        if not user:
            raise NotFoundException(detail="User not found")

        update_data = data.model_dump(exclude_unset=True, exclude_none=True)
        
        if update_data:
            await User.update(update_data).where(User.id == user_id)
        
        return await self.get_by_id(user_id)

    async def authenticate(self, email: str, password: str) -> User:
        """Authenticate user with email and password."""
        user = await self.get_by_email(email)
        
        if not user:
            raise UnauthorizedException(detail="Invalid email or password")
        
        if not self.verify_password(password, user["password_hash"]):
            raise UnauthorizedException(detail="Invalid email or password")
        
        if not user["is_active"]:
            raise UnauthorizedException(detail="Account is disabled")

        # Update last login
        await User.update({"last_login_at": datetime.now()}).where(User.id == user["id"])
        
        logger.info(f"User {email} authenticated successfully")
        return user

    async def change_password(
        self, user_id: UUID, current_password: str, new_password: str
    ) -> bool:
        """Change user password."""
        user = await self.get_by_id(user_id)
        if not user:
            raise NotFoundException(detail="User not found")

        if not self.verify_password(current_password, user["password_hash"]):
            raise UnauthorizedException(detail="Current password is incorrect")

        new_hash = self.hash_password(new_password)
        await User.update({"password_hash": new_hash}).where(User.id == user_id)
        
        logger.info(f"Password changed for user {user_id}")
        return True

    async def get_user_stats(self, user_id: UUID) -> dict[str, Any]:
        """Get user statistics."""
        from app.db.tables import ConversationSession, ExamAttempt

        # Get exam attempts
        attempts = await ExamAttempt.count().where(ExamAttempt.user == user_id)
        completed = await ExamAttempt.count().where(
            (ExamAttempt.user == user_id) & (ExamAttempt.status == "completed")
        )

        # Get conversation sessions
        sessions = await ConversationSession.count().where(
            ConversationSession.user == user_id
        )

        return {
            "total_exams": attempts,
            "completed_exams": completed,
            "conversation_sessions": sessions,
        }


# Singleton instance
user_service = UserService()
