"""Schemas for AI-agent practice sessions (topic generation & live exams)."""

from __future__ import annotations

from typing import Any

from app.schemas.base import BaseSchema, JsonDict, JsonList
from pydantic import Field

# ── Topic Generation ──────────────────────────────────────────────


class TopicGenerateRequest(BaseSchema):
    """Request body for generating IELTS practice topics."""

    target_exam: str = Field(default="ielts", pattern="^(ielts|ielts_academic|ielts_general)$")
    target_score: float | None = Field(default=None, ge=1.0, le=9.0)
    current_level_description: str | None = Field(
        default=None,
        max_length=2000,
        description="Free-text self-assessment of current English level.",
    )
    section_focus: str | None = Field(
        default=None,
        pattern="^(listening|reading|writing|speaking)$",
        description="Generate topics for a specific section only.",
    )
    preferences: JsonDict = Field(default_factory=dict)


class TopicGenerateResponse(BaseSchema):
    """Response with generated IELTS topics and level assessment."""

    estimated_band: float | None = None
    band_range: str | None = None
    section_estimates: JsonDict = {}
    strengths: JsonList = []
    weaknesses: JsonList = []
    assessment_summary: str | None = None
    speaking_topics: JsonList = []
    writing_topics: JsonList = []
    reading_topics: JsonList = []
    listening_topics: JsonList = []
    study_plan_notes: str | None = None


# ── Practice Exam Session ─────────────────────────────────────────


class PracticeExamStartRequest(BaseSchema):
    """Request body for starting an AI-powered practice exam."""

    exam_type: str = Field(
        default="ielts_academic",
        pattern="^(ielts_academic|ielts_general)$",
    )
    section: str = Field(pattern="^(speaking|writing|reading|listening)$")
    difficulty: str = Field(
        default="intermediate",
        pattern="^(beginner|intermediate|advanced|expert)$",
    )
    target_band: float | None = Field(default=None, ge=1.0, le=9.0)
    topic: str | None = Field(default=None, max_length=200)


class PracticeExamAnswerRequest(BaseSchema):
    """Request body for submitting an answer in a practice session."""

    thread_id: str = Field(min_length=1)
    answer: str = Field(min_length=1, max_length=10000)


class PracticeExamStateRequest(BaseSchema):
    """Request body for fetching current session state."""

    thread_id: str = Field(min_length=1)


class PracticeExamQuestionResponse(BaseSchema):
    """Response when the exam has a next question ready."""

    thread_id: str
    status: str
    section: str | None = None
    current_part: int = 1
    question_index: int = 0
    total_questions: int = 0
    current_question: JsonDict | None = None


class PracticeExamReportResponse(BaseSchema):
    """Response when the exam is completed."""

    thread_id: str
    status: str = "completed"
    section: str | None = None
    overall_band: float | None = None
    section_scores: JsonList = []
    evaluations: JsonList = []
    final_report_markdown: str | None = None
