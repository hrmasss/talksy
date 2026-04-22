"""State definition for the IELTS exam agent graph."""

from __future__ import annotations

from typing import Annotated, Any, Literal

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages
from typing_extensions import TypedDict

# ---------------------------------------------------------------------------
# IELTS configuration constants
# ---------------------------------------------------------------------------

IELTS_SECTIONS = ["speaking", "writing", "reading", "listening"]

SPEAKING_PARTS = {
    1: {
        "name": "Introduction & Interview",
        "duration_minutes": 5,
        "description": "Familiar topics about home, family, work, studies, interests.",
        "num_questions": 4,
    },
    2: {
        "name": "Long Turn (Cue Card)",
        "duration_minutes": 4,
        "description": "1 min preparation, 1-2 min monologue on the cue card topic.",
        "num_questions": 1,
    },
    3: {
        "name": "Discussion",
        "duration_minutes": 5,
        "description": "More abstract ideas linked to Part 2 topic.",
        "num_questions": 3,
    },
}

WRITING_TASKS = {
    1: {
        "name": "Task 1",
        "duration_minutes": 20,
        "min_words": 150,
        "description": "Describe visual data (Academic) or write a letter (General Training).",
    },
    2: {
        "name": "Task 2",
        "duration_minutes": 40,
        "min_words": 250,
        "description": "Write an essay discussing a point of view, argument, or problem.",
    },
}

BAND_DESCRIPTORS = {
    9: "Expert user",
    8: "Very good user",
    7: "Good user",
    6: "Competent user",
    5: "Modest user",
    4: "Limited user",
    3: "Extremely limited user",
}

DIFFICULTY_PRESETS = {
    "beginner": {"target_band": "4.0-5.0", "total_questions": 8},
    "intermediate": {"target_band": "5.5-6.5", "total_questions": 10},
    "advanced": {"target_band": "7.0-8.0", "total_questions": 12},
    "expert": {"target_band": "8.0-9.0", "total_questions": 12},
}


def get_difficulty_info(level: str) -> dict:
    return DIFFICULTY_PRESETS.get(level, DIFFICULTY_PRESETS["intermediate"])


# ---------------------------------------------------------------------------
# Exam state
# ---------------------------------------------------------------------------

class ExamState(TypedDict):
    """State flowing through the IELTS exam LangGraph."""

    # --- Conversation history (for the LLM) --------------------------------
    messages: Annotated[list[BaseMessage], add_messages]

    # --- Exam configuration ------------------------------------------------
    user_id: str
    exam_section: Literal["speaking", "writing", "reading", "listening"]
    difficulty_level: str                  # "beginner" | "intermediate" | …
    target_band: str                       # e.g. "6.0-7.0"
    exam_variant: str                      # "academic" | "general_training"
    total_questions: int
    time_per_question: int | None       # seconds, None = no timer

    # --- Question management -----------------------------------------------
    current_question: str | None
    current_question_type: str | None
    current_question_passage: str | None
    current_part: int | None            # Speaking part or Writing task number
    question_number: int
    questions_asked: list[dict[str, Any]]
    question_bank: list[dict[str, Any]]
    current_question_options: list[str] | None
    current_question_time_limit_seconds: int | None

    # --- Answer management -------------------------------------------------
    current_answer: str | None
    candidate_answers: list[dict[str, Any]]

    # --- Performance tracking ----------------------------------------------
    performance_scores: list[float]
    current_phase: str                     # "warm_up" | "main" | "wrap_up"

    # --- Evaluation --------------------------------------------------------
    current_evaluation: dict[str, Any] | None
    final_band_score: float | None
    final_report: str | None

    # --- Control -----------------------------------------------------------
    should_continue: bool
    status: str                            # "in_progress" | "completed" | "failed"
    error_message: str | None
