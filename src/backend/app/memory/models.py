"""Pydantic models and enums for the long-term memory system."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Memory categories
# ---------------------------------------------------------------------------

class MemoryCategory(str, Enum):
    """Categories for organising user memories in Qdrant.

    Each category maps to a logical area of the user's learning journey.
    """

    # Exam-section skills
    WRITING = "writing"
    SPEAKING = "speaking"
    READING = "reading"
    LISTENING = "listening"

    # Cross-cutting
    VOCABULARY = "vocabulary"
    GRAMMAR = "grammar"
    PRONUNCIATION = "pronunciation"

    # Meta / behavioural
    USER_ACTIVITY = "user_activity"       # general activity log
    EXAM_RESULT = "exam_result"           # completed exam summaries
    STUDY_PREFERENCE = "study_preference" # preferred topics, schedule, etc.
    STRENGTH = "strength"                 # known strengths
    WEAKNESS = "weakness"                 # known weaknesses
    GOAL = "goal"                         # user goals & target scores
    FEEDBACK = "feedback"                 # aggregated feedback & tips


# ---------------------------------------------------------------------------
# Memory entry
# ---------------------------------------------------------------------------

class MemoryEntry(BaseModel):
    """A single piece of long-term memory to store in Qdrant."""

    id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    user_id: str = Field(..., description="Owner of this memory")
    category: MemoryCategory = Field(..., description="Memory category")
    content: str = Field(..., description="Main textual content to embed & store")
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Arbitrary structured metadata (scores, dates, tags …)",
    )
    importance: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="How important is this memory (0 = trivial, 1 = critical)",
    )
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    # Convenience ----------------------------------------------------------

    def to_qdrant_payload(self) -> dict[str, Any]:
        """Flatten to a dict suitable for Qdrant point payload."""
        return {
            "user_id": self.user_id,
            "category": self.category.value,
            "content": self.content,
            "importance": self.importance,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            **self.metadata,
        }


# ---------------------------------------------------------------------------
# Search result wrapper
# ---------------------------------------------------------------------------

class MemorySearchResult(BaseModel):
    """A memory entry enriched with a relevance score from vector search."""

    entry: MemoryEntry
    score: float = Field(description="Cosine similarity score from Qdrant")


# ---------------------------------------------------------------------------
# Bulk progress summary (returned by get_user_progress_summary)
# ---------------------------------------------------------------------------

class UserProgressSummary(BaseModel):
    """Aggregated snapshot of a user's progress across all categories."""

    user_id: str
    total_memories: int = 0
    categories: dict[str, int] = Field(
        default_factory=dict,
        description="Count of memories per category",
    )
    recent_exam_results: list[dict[str, Any]] = Field(default_factory=list)
    strengths: list[str] = Field(default_factory=list)
    weaknesses: list[str] = Field(default_factory=list)
    goals: list[str] = Field(default_factory=list)
    latest_activity: str | None = None
