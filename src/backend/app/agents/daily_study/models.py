"""Pydantic models for daily study plan structured outputs."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class DailyStudyActivityModel(BaseModel):
    """One generated activity in a daily study plan."""

    section: str = Field(default="vocabulary")
    activity_type: str = Field(default="vocabulary_practice")
    title: str = Field(default="Practice Activity")
    content: dict[str, Any] = Field(default_factory=dict)
    difficulty_level: int = Field(default=1, ge=1, le=5)


class DailyStudyPlanModel(BaseModel):
    """Generated daily plan payload."""

    activities: list[DailyStudyActivityModel] = Field(default_factory=list)
    rationale: str = Field(default="")


class StudyActivityFeedbackModel(BaseModel):
    """Evaluation payload for one submitted study activity response."""

    band_score: float = Field(default=5.0, ge=0, le=9)
    feedback: str = Field(default="Evaluation completed.")
    suggestions: list[str] = Field(default_factory=list)
    is_correct: bool | None = None
