"""Schemas for the IELTS preparation platform."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any
from uuid import UUID

from app.schemas.base import BaseSchema, JsonDict, JsonList
from pydantic import Field


# ── User Profile ──────────────────────────────────────────────────

class IELTSProfileUpdate(BaseSchema):
    """Update IELTS-specific user profile fields."""

    target_band_score: float | None = Field(default=None, ge=1.0, le=9.0)
    exam_date: date | None = None
    preferred_daily_practice_time: int | None = Field(default=None, ge=5, le=480)
    current_estimated_band: float | None = Field(default=None, ge=0, le=9.0)


class IELTSProfileResponse(BaseSchema):
    """IELTS profile data returned to the client."""

    target_band_score: float | None = None
    exam_date: date | None = None
    preferred_daily_practice_time: int | None = None
    current_estimated_band: float | None = None
    skill_profile: JsonDict = {}
    section_scores: JsonDict = {}
    onboarding_completed: bool = False


# ── Placement Test (Onboarding) ──────────────────────────────────

class PlacementStartRequest(BaseSchema):
    """Start the initial placement test."""

    target_band_score: float | None = Field(default=None, ge=1.0, le=9.0)
    exam_date: date | None = None


class PlacementAnswerRequest(BaseSchema):
    """Submit an answer during placement test."""

    thread_id: str = Field(min_length=1)
    answer: str = Field(min_length=1, max_length=10000)


class PlacementQuestionResponse(BaseSchema):
    """A question from the placement test."""

    thread_id: str
    status: str  # in_progress, awaiting_answer
    section: str  # listening, reading, writing, speaking
    question_index: int
    total_questions: int
    question_text: str
    question_type: str  # multiple_choice, fill_blank, essay, speaking
    options: list[str] = []
    time_limit_seconds: int | None = None


class PlacementResultResponse(BaseSchema):
    """Final result of the placement test."""

    thread_id: str
    status: str = "completed"
    overall_band: float
    listening_band: float
    reading_band: float
    writing_band: float
    speaking_band: float
    skill_profile: JsonDict = {}
    strengths: list[str] = []
    weaknesses: list[str] = []
    focus_areas: list[str] = []
    feedback_markdown: str | None = None


# ── Mock Test ─────────────────────────────────────────────────────

class MockTestStartRequest(BaseSchema):
    """Start a mock IELTS test."""

    test_type: str = Field(
        default="section",
        pattern="^(full|section)$",
    )
    section: str | None = Field(
        default=None,
        pattern="^(listening|reading|writing|speaking)$",
        description="Required when test_type is 'section'.",
    )
    difficulty: str = Field(
        default="adaptive",
        pattern="^(beginner|intermediate|advanced|expert|adaptive)$",
    )


class MockTestQuestionResponse(BaseSchema):
    """A question during a mock test."""

    thread_id: str
    status: str
    section: str
    current_part: int = 1
    question_index: int
    total_questions: int
    question_text: str
    question_type: str
    options: list[str] = []
    passage: str | None = None
    time_limit_seconds: int | None = None


class MockTestAnswerRequest(BaseSchema):
    """Submit an answer in a mock test."""

    thread_id: str = Field(min_length=1)
    answer: str = Field(min_length=1, max_length=10000)


class MockTestReportResponse(BaseSchema):
    """Final mock test report."""

    thread_id: str
    status: str = "completed"
    section: str | None = None
    overall_band: float | None = None
    section_scores: JsonList = []
    evaluations: JsonList = []
    strengths: list[str] = []
    weaknesses: list[str] = []
    recommendations: list[str] = []
    final_report_markdown: str | None = None


# ── Daily Study ───────────────────────────────────────────────────

class DailyStudyPlanResponse(BaseSchema):
    """Today's study plan."""

    id: UUID
    study_date: date
    activities: JsonList = []
    completed_count: int = 0
    total_count: int = 0
    is_completed: bool = False
    ai_rationale: str | None = None


class DailyStudyHistoryResponse(BaseSchema):
    """List of recent daily study plans."""

    items: list[DailyStudyPlanResponse] = []


class StudyActivityResponse(BaseSchema):
    """A single study activity."""

    id: UUID
    section: str
    activity_type: str
    title: str
    content: JsonDict = {}
    difficulty_level: int = 1
    is_completed: bool = False
    ai_feedback: JsonDict = {}
    band_score: float | None = None


class StudyActivitySubmitRequest(BaseSchema):
    """Submit response to a study activity."""

    activity_id: UUID
    response: str = Field(min_length=1, max_length=10000)
    time_spent_seconds: int = 0


class StudyActivityFeedbackResponse(BaseSchema):
    """Feedback after submitting a study activity."""

    activity_id: UUID
    band_score: float | None = None
    feedback: JsonDict = {}
    is_correct: bool | None = None
    suggestions: list[str] = []


# ── Progress Tracking ─────────────────────────────────────────────

class ProgressOverviewResponse(BaseSchema):
    """Overall progress overview."""

    current_estimated_band: float | None = None
    target_band_score: float | None = None
    days_until_exam: int | None = None
    total_tests_taken: int = 0
    total_activities_completed: int = 0
    section_scores: JsonDict = {}
    skill_profile: JsonDict = {}
    recent_scores: JsonList = []
    score_history: JsonList = []
    strengths: list[str] = []
    weaknesses: list[str] = []
    recommendations: list[str] = []


class TestHistoryResponse(BaseSchema):
    """List of past test results."""

    items: list[dict[str, Any]] = []
    total: int = 0
