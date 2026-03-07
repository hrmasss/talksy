"""Conversation-related schemas."""

from datetime import datetime
from typing import Any
from uuid import UUID

from app.schemas.base import BaseSchema, JsonDict, JsonList
from pydantic import Field


class ConversationStart(BaseSchema):
    """Schema for starting a conversation session."""

    topic: str = Field(min_length=1, max_length=255)
    scenario: str | None = None
    difficulty_level: int = Field(default=1, ge=1, le=5)


class ConversationMessage(BaseSchema):
    """Schema for a conversation message."""

    content: str = Field(min_length=1)
    audio_url: str | None = None


class ConversationMessageResponse(BaseSchema):
    """Schema for conversation message response."""

    id: UUID
    role: str
    content: str
    audio_url: str | None = None
    timestamp: datetime
    analysis: JsonDict = {}


class ConversationResponse(BaseSchema):
    """Schema for AI conversation response."""

    message: ConversationMessageResponse
    suggestions: JsonList = []
    vocabulary_tips: JsonList = []
    grammar_notes: JsonList = []


class ConversationSessionResponse(BaseSchema):
    """Schema for conversation session response."""

    id: UUID
    user_id: UUID
    topic: str
    scenario: str | None = None
    difficulty_level: int
    started_at: datetime
    ended_at: datetime | None = None
    duration_seconds: int
    message_count: int
    vocabulary_used: JsonList = []
    grammar_score: float | None = None
    fluency_score: float | None = None
    coherence_score: float | None = None
    overall_score: float | None = None
    ai_summary: str | None = None
    ai_suggestions: JsonList = []


class ConversationHistoryResponse(BaseSchema):
    """Schema for conversation history."""

    session: ConversationSessionResponse
    messages: list[ConversationMessageResponse]


class ConversationAnalysisResponse(BaseSchema):
    """Schema for detailed conversation analysis."""

    session_id: UUID
    grammar_score: float
    fluency_score: float
    coherence_score: float
    vocabulary_score: float
    overall_score: float
    strengths: JsonList
    areas_for_improvement: JsonList
    vocabulary_analysis: JsonDict
    grammar_errors: JsonList
    suggestions: JsonList
