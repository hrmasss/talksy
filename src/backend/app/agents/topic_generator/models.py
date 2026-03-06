"""Pydantic models for structured LLM output in the topic generator."""

from __future__ import annotations

from typing import List, Literal, Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Level assessment
# ---------------------------------------------------------------------------

class LevelAssessment(BaseModel):
    """Result of assessing a user's current IELTS band range."""

    estimated_band: float = Field(
        description="Estimated overall band score (e.g. 5.5, 6.0, 7.0)"
    )
    band_range: str = Field(
        description="Band range bucket, e.g. '5.0-5.5', '6.0-6.5'"
    )
    strengths: List[str] = Field(
        default_factory=list,
        description="Skills / areas the user is already good at",
    )
    weaknesses: List[str] = Field(
        default_factory=list,
        description="Skills / areas that need improvement",
    )
    section_estimates: dict = Field(
        default_factory=dict,
        description="Per-section estimates, e.g. {'listening': 6.0, 'reading': 5.5, …}",
    )
    summary: str = Field(description="Short narrative summary of the assessment")


# ---------------------------------------------------------------------------
# Speaking topics
# ---------------------------------------------------------------------------

class SpeakingTopic(BaseModel):
    """One IELTS Speaking practice topic."""

    part: Literal[1, 2, 3] = Field(description="IELTS Speaking part (1, 2 or 3)")
    topic: str = Field(description="Topic title, e.g. 'Hobbies and Leisure'")
    cue_card: Optional[str] = Field(
        None,
        description="Cue card text (Part 2 only)",
    )
    questions: List[str] = Field(
        description="Follow-up or discussion questions"
    )
    vocabulary_hints: List[str] = Field(
        default_factory=list,
        description="Key vocabulary useful for this topic",
    )
    target_band: str = Field(
        description="Target band range, e.g. '6.0-7.0'"
    )


# ---------------------------------------------------------------------------
# Writing topics
# ---------------------------------------------------------------------------

class WritingTopic(BaseModel):
    """One IELTS Writing practice topic."""

    task: Literal[1, 2] = Field(description="IELTS Writing task (1 or 2)")
    task_type: str = Field(
        description="e.g. 'bar chart', 'line graph', 'opinion essay', 'discussion essay'"
    )
    prompt: str = Field(description="Full writing prompt / task description")
    sample_outline: Optional[str] = Field(
        None,
        description="Suggested paragraph outline for guidance",
    )
    key_vocabulary: List[str] = Field(default_factory=list)
    target_band: str = Field(description="Target band range")


# ---------------------------------------------------------------------------
# Reading topics
# ---------------------------------------------------------------------------

class ReadingTopic(BaseModel):
    """A reading passage theme with sample question types."""

    passage_theme: str = Field(description="Theme of the passage, e.g. 'Space Exploration'")
    question_types: List[str] = Field(
        description="Question types used, e.g. ['True/False/NG', 'Matching Headings']"
    )
    difficulty: Literal["easy", "medium", "hard"] = Field(description="Difficulty level")
    target_band: str = Field(description="Target band range")


# ---------------------------------------------------------------------------
# Listening topics
# ---------------------------------------------------------------------------

class ListeningTopic(BaseModel):
    """A listening section practice topic."""

    section: Literal[1, 2, 3, 4] = Field(description="IELTS Listening section (1-4)")
    scenario: str = Field(description="Scenario description, e.g. 'Booking a hotel room'")
    question_types: List[str] = Field(
        description="e.g. ['form completion', 'multiple choice']"
    )
    difficulty: Literal["easy", "medium", "hard"] = Field(description="Difficulty level")
    target_band: str = Field(description="Target band range")


# ---------------------------------------------------------------------------
# Complete topic set
# ---------------------------------------------------------------------------

class TopicSet(BaseModel):
    """Full set of generated practice topics across all IELTS sections."""

    speaking_topics: List[SpeakingTopic] = Field(default_factory=list)
    writing_topics: List[WritingTopic] = Field(default_factory=list)
    reading_topics: List[ReadingTopic] = Field(default_factory=list)
    listening_topics: List[ListeningTopic] = Field(default_factory=list)
    target_band: str = Field(description="Overall target band range for this set")
    study_plan_notes: str = Field(
        default="",
        description="Short guidance on how to use these topics effectively",
    )
