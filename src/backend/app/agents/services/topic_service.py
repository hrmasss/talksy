"""Service layer for the IELTS topic generator agent.

Thin wrapper around the LangGraph so the API layer doesn't need to
know about graph internals.
"""

from __future__ import annotations

import uuid
from typing import Any

from app.core.logging import logger

from ..topic_generator.graph import run_topic_generator, stream_topic_generator


class TopicGeneratorService:
    """Generate IELTS practice topics for a user."""

    async def generate_topics(
        self,
        *,
        user_id: str,
        target_exam: str = "ielts",
        target_score: float | None = None,
        current_level_description: str | None = None,
        section_focus: str | None = None,
        preferences: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Run the full topic-generation pipeline and return the result.

        Returns a dict with keys:
            estimated_band, band_range, section_estimates,
            strengths, weaknesses, assessment_summary,
            speaking_topics, writing_topics, reading_topics,
            listening_topics, study_plan_notes
        """
        thread_id = f"topics_{user_id}_{uuid.uuid4().hex[:8]}"

        initial: dict[str, Any] = {
            "user_id": user_id,
            "target_exam": target_exam,
            "target_score": target_score,
            "current_level_description": current_level_description,
            "section_focus": section_focus,
            "preferences": preferences or {},
            # defaults that the graph expects
            "strengths": [],
            "weaknesses": [],
            "speaking_topics": [],
            "writing_topics": [],
            "reading_topics": [],
            "listening_topics": [],
            "status": "processing",
            "progress": 0.0,
        }

        logger.info(f"Generating topics for user {user_id} (thread {thread_id})")
        result = await run_topic_generator(initial, thread_id=thread_id)
        logger.info(f"Topic generation complete – status={result.get('status')}")

        return {
            "estimated_band": result.get("estimated_band"),
            "band_range": result.get("band_range"),
            "section_estimates": result.get("section_estimates"),
            "strengths": result.get("strengths", []),
            "weaknesses": result.get("weaknesses", []),
            "assessment_summary": result.get("assessment_summary"),
            "speaking_topics": result.get("speaking_topics", []),
            "writing_topics": result.get("writing_topics", []),
            "reading_topics": result.get("reading_topics", []),
            "listening_topics": result.get("listening_topics", []),
            "study_plan_notes": result.get("study_plan_notes"),
        }

    async def stream_topics(
        self,
        *,
        user_id: str,
        target_exam: str = "ielts",
        target_score: float | None = None,
        current_level_description: str | None = None,
        section_focus: str | None = None,
        preferences: dict[str, Any] | None = None,
    ):
        """Yield intermediate states for streaming UX."""
        thread_id = f"topics_{user_id}_{uuid.uuid4().hex[:8]}"

        initial: dict[str, Any] = {
            "user_id": user_id,
            "target_exam": target_exam,
            "target_score": target_score,
            "current_level_description": current_level_description,
            "section_focus": section_focus,
            "preferences": preferences or {},
            "strengths": [],
            "weaknesses": [],
            "speaking_topics": [],
            "writing_topics": [],
            "reading_topics": [],
            "listening_topics": [],
            "status": "processing",
            "progress": 0.0,
        }

        async for state in stream_topic_generator(initial, thread_id=thread_id):
            yield state


# Module-level singleton
topic_generator_service = TopicGeneratorService()
