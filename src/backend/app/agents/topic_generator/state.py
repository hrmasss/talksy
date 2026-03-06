"""State definition for the IELTS topic generator graph."""

from __future__ import annotations

from typing import Any

from typing_extensions import TypedDict


class TopicGeneratorState(TypedDict):
    """State that flows through the topic-generator LangGraph."""

    # --- user input --------------------------------------------------------
    user_id: str
    target_exam: str                       # "ielts" (extensible to pte/toefl)
    target_score: float | None          # desired overall band, e.g. 7.0
    current_level_description: str | None  # free-text self-assessment
    section_focus: str | None           # "speaking", "writing", … or None for all
    preferences: dict[str, Any] | None  # e.g. {"academic": True}

    # --- assessment output -------------------------------------------------
    estimated_band: float | None
    band_range: str | None
    section_estimates: dict[str, float] | None
    strengths: list[str]
    weaknesses: list[str]
    assessment_summary: str | None

    # --- generated topics --------------------------------------------------
    speaking_topics: list[dict[str, Any]]
    writing_topics: list[dict[str, Any]]
    reading_topics: list[dict[str, Any]]
    listening_topics: list[dict[str, Any]]
    study_plan_notes: str | None

    # --- workflow control --------------------------------------------------
    status: str         # "processing" | "completed" | "failed"
    error_message: str | None
    progress: float     # 0.0 – 100.0
