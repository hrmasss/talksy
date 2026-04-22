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


class StudyActivityCompletionModel(BaseModel):
    """Confirmation payload returned after completing a study activity."""

    message: str = Field(default="Your work has been saved.")
    next_steps: list[str] = Field(default_factory=list)
    saved_response: bool = Field(default=True)
