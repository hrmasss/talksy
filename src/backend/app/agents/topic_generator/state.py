"""State definition for the IELTS topic generator graph."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from typing_extensions import TypedDict


class TopicGeneratorState(TypedDict):
    """State that flows through the topic-generator LangGraph."""

    # --- user input --------------------------------------------------------
    user_id: str
    target_exam: str                       # "ielts" (extensible to pte/toefl)
    target_score: Optional[float]          # desired overall band, e.g. 7.0
    current_level_description: Optional[str]  # free-text self-assessment
    section_focus: Optional[str]           # "speaking", "writing", … or None for all
    preferences: Optional[Dict[str, Any]]  # e.g. {"academic": True}

    # --- assessment output -------------------------------------------------
    estimated_band: Optional[float]
    band_range: Optional[str]
    section_estimates: Optional[Dict[str, float]]
    strengths: List[str]
    weaknesses: List[str]
    assessment_summary: Optional[str]

    # --- generated topics --------------------------------------------------
    speaking_topics: List[Dict[str, Any]]
    writing_topics: List[Dict[str, Any]]
    reading_topics: List[Dict[str, Any]]
    listening_topics: List[Dict[str, Any]]
    study_plan_notes: Optional[str]

    # --- workflow control --------------------------------------------------
    status: str         # "processing" | "completed" | "failed"
    error_message: Optional[str]
    progress: float     # 0.0 – 100.0
