"""State definition for the IELTS placement test agent."""

from __future__ import annotations

from typing import Annotated, Any

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages
from typing_extensions import TypedDict

# Placement test: 3-5 min per section, 4 sections
PLACEMENT_SECTIONS = ["listening", "reading", "writing", "speaking"]

PLACEMENT_QUESTIONS_PER_SECTION = {
    "listening": 3,
    "reading": 3,
    "writing": 1,
    "speaking": 2,
}

TOTAL_PLACEMENT_QUESTIONS = sum(PLACEMENT_QUESTIONS_PER_SECTION.values())


class PlacementState(TypedDict):
    """State flowing through the placement test LangGraph."""

    messages: Annotated[list[BaseMessage], add_messages]

    # User info
    user_id: str
    target_band_score: float | None

    # Test progress
    current_section: str  # listening, reading, writing, speaking
    current_section_index: int
    question_number: int  # global question counter
    section_question_number: int  # question counter within current section
    total_questions: int

    # Current question
    current_question: str | None
    current_question_type: str | None
    current_options: list[str]

    # Responses
    responses: list[dict[str, Any]]  # all Q&A pairs with evaluations
    current_answer: str | None

    # Evaluation
    section_scores: dict[str, float]  # {listening: 6.0, reading: 5.5, ...}
    overall_band: float | None

    # Skill profile
    strengths: list[str]
    weaknesses: list[str]
    focus_areas: list[str]
    feedback_markdown: str | None

    # Control
    status: str  # in_progress, evaluating, completed
    error_message: str | None
