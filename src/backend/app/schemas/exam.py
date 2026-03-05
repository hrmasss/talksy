"""Exam-related schemas."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import Field

from app.schemas.base import BaseSchema, TimestampMixin


class ExamCreate(BaseSchema):
    """Schema for creating a new exam."""

    exam_type: str = Field(pattern="^(ielts|pte|toefl)$")
    title: str = Field(min_length=1, max_length=255)
    description: str | None = None
    section: str = Field(pattern="^(listening|reading|writing|speaking)$")
    duration_minutes: int = Field(ge=1, le=300)
    total_questions: int = Field(ge=1)
    instructions: str | None = None
    difficulty_level: int = Field(default=1, ge=1, le=5)
    is_active: bool = True
    is_free: bool = False
    metadata: dict[str, Any] = {}


class ExamUpdate(BaseSchema):
    """Schema for updating exam information."""

    title: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    instructions: str | None = None
    difficulty_level: int | None = Field(default=None, ge=1, le=5)
    is_active: bool | None = None
    is_free: bool | None = None
    metadata: dict[str, Any] | None = None


class ExamResponse(BaseSchema, TimestampMixin):
    """Schema for exam response."""

    id: UUID
    exam_type: str
    title: str
    description: str | None = None
    section: str
    duration_minutes: int
    total_questions: int
    instructions: str | None = None
    difficulty_level: int
    is_active: bool
    is_free: bool
    metadata: dict[str, Any] = {}


class ExamListResponse(BaseSchema):
    """Schema for exam list response."""

    items: list[ExamResponse]
    total: int
    page: int
    page_size: int


class QuestionCreate(BaseSchema):
    """Schema for creating a question."""

    exam_id: UUID
    question_type: str
    question_number: int
    question_text: str
    question_audio_url: str | None = None
    question_image_url: str | None = None
    options: list[dict[str, Any]] = []
    correct_answer: Any
    explanation: str | None = None
    points: float = 1.0
    time_limit_seconds: int | None = None
    hints: list[str] = []
    tags: list[str] = []


class QuestionResponse(BaseSchema):
    """Schema for question response (without correct answer)."""

    id: UUID
    question_type: str
    question_number: int
    question_text: str
    question_audio_url: str | None = None
    question_image_url: str | None = None
    options: list[dict[str, Any]] = []
    points: float
    time_limit_seconds: int | None = None
    hints: list[str] = []


class ExamAttemptCreate(BaseSchema):
    """Schema for starting an exam attempt."""

    exam_id: UUID


class ExamAttemptResponse(BaseSchema):
    """Schema for exam attempt response."""

    id: UUID
    user_id: UUID
    exam_id: UUID
    started_at: datetime
    completed_at: datetime | None = None
    time_spent_seconds: int
    score: float | None = None
    max_score: float | None = None
    band_score: float | None = None
    status: str
    feedback: dict[str, Any] = {}
    ai_analysis: dict[str, Any] = {}


class AnswerSubmit(BaseSchema):
    """Schema for submitting an answer."""

    question_id: UUID
    user_answer: Any
    audio_response_url: str | None = None
    time_spent_seconds: int = 0


class AnswerResponse(BaseSchema):
    """Schema for answer response."""

    id: UUID
    question_id: UUID
    user_answer: Any
    is_correct: bool | None = None
    points_earned: float
    ai_feedback: dict[str, Any] = {}


class ExamResultResponse(BaseSchema):
    """Schema for complete exam results."""

    attempt: ExamAttemptResponse
    answers: list[AnswerResponse]
    summary: dict[str, Any] = {}
    recommendations: list[str] = []
