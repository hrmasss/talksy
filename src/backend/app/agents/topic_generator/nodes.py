"""Graph nodes for the IELTS topic generator."""

from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from app.config import settings
from app.core.logging import logger

from ..common.llm import get_llm
from .models import (
    LevelAssessment,
    ListeningTopicList,
    ReadingTopicList,
    SpeakingTopicList,
    WritingTopicList,
)
from .prompts import (
    ASSESS_LEVEL_PROMPT,
    GENERATE_LISTENING_TOPICS_PROMPT,
    GENERATE_READING_TOPICS_PROMPT,
    GENERATE_SPEAKING_TOPICS_PROMPT,
    GENERATE_WRITING_TOPICS_PROMPT,
)
from .state import TopicGeneratorState


def _time_ctx() -> dict:
    now = datetime.now(ZoneInfo("UTC"))
    return {
        "current_datetime": now.strftime("%Y-%m-%d %H:%M:%S %Z"),
        "current_year": now.year,
    }


# ============================================================================
# 1. Assess Level
# ============================================================================

async def assess_level_node(state: TopicGeneratorState) -> dict:
    """Estimate the user's IELTS band from their self-description."""
    logger.info("Assessing user IELTS level")

    llm = get_llm(model=settings.gemini_model, temperature=0.5)
    structured = llm.with_structured_output(LevelAssessment)

    ctx = _time_ctx()
    response: LevelAssessment = await structured.ainvoke(
        ASSESS_LEVEL_PROMPT.format_messages(
            target_exam=state.get("target_exam", "ielts"),
            target_score=state.get("target_score") or "Not specified",
            current_level_description=state.get(
                "current_level_description"
            ) or "No information provided",
            preferences=str(state.get("preferences") or {}),
            **ctx,
        )
    )

    data = response.model_dump()
    target = state.get("target_score")
    band_range = data["band_range"]
    if target:
        band_range = f"{data['estimated_band']:.1f} → {target:.1f}"

    logger.info("Estimated band: {} ({})", data['estimated_band'], band_range)

    return {
        "estimated_band": data["estimated_band"],
        "band_range": band_range,
        "section_estimates": data.get("section_estimates", {}),
        "strengths": data.get("strengths", []),
        "weaknesses": data.get("weaknesses", []),
        "assessment_summary": data.get("summary", ""),
        "status": "processing",
        "progress": 20.0,
    }


# ============================================================================
# 2. Generate Topics (concurrent per section)
# ============================================================================

async def generate_topics_node(state: TopicGeneratorState) -> dict:
    """Generate practice topics for all (or a focused) IELTS section."""
    logger.info("Generating IELTS practice topics")

    band_range = state.get("band_range", "5.5-6.0")
    target_band = f"{state.get('target_score', 6.5):.1f}"
    weaknesses = str(state.get("weaknesses", []))
    section_focus = state.get("section_focus")  # None = all sections
    exam_variant = (state.get("preferences") or {}).get("variant", "academic")
    ctx = _time_ctx()
    num_topics = 4  # per section

    common = {
        "band_range": band_range,
        "target_band": target_band,
        "weaknesses": weaknesses,
        "num_topics": num_topics,
        **ctx,
    }

    llm = get_llm(model=settings.gemini_model, temperature=0.8)

    # Build section generators ------------------------------------------------
    tasks: dict[str, Any] = {}

    if section_focus in (None, "speaking"):
        async def _speaking():
            s_llm2 = llm.with_structured_output(SpeakingTopicList)
            r = await s_llm2.ainvoke(
                GENERATE_SPEAKING_TOPICS_PROMPT.format_messages(**common)
            )
            return [t.model_dump() for t in r.topics]
        tasks["speaking"] = _speaking()

    if section_focus in (None, "writing"):
        async def _writing():
            w_llm = llm.with_structured_output(WritingTopicList)
            r = await w_llm.ainvoke(
                GENERATE_WRITING_TOPICS_PROMPT.format_messages(
                    exam_variant=exam_variant, **common
                )
            )
            return [t.model_dump() for t in r.topics]
        tasks["writing"] = _writing()

    if section_focus in (None, "reading"):
        async def _reading():
            r_llm = llm.with_structured_output(ReadingTopicList)
            r = await r_llm.ainvoke(
                GENERATE_READING_TOPICS_PROMPT.format_messages(**common)
            )
            return [t.model_dump() for t in r.topics]
        tasks["reading"] = _reading()

    if section_focus in (None, "listening"):
        async def _listening():
            l_llm = llm.with_structured_output(ListeningTopicList)
            r = await l_llm.ainvoke(
                GENERATE_LISTENING_TOPICS_PROMPT.format_messages(**common)
            )
            return [t.model_dump() for t in r.topics]
        tasks["listening"] = _listening()

    # Run all in parallel
    keys = list(tasks.keys())
    results = await asyncio.gather(*tasks.values(), return_exceptions=True)

    out: dict[str, list] = {}
    # ensure the keys and results lists are the same length
    for key, result in zip(keys, results, strict=True):
        if isinstance(result, Exception):
            logger.warning("{} topic generation failed: {}", key, result)
            out[key] = []
        else:
            out[key] = result
            logger.info("{}: {} topics generated", key, len(result))

    study_plan = (
        f"Focus on your weaknesses: {', '.join(state.get('weaknesses', []))}. "
        f"Practice each section regularly and time yourself under exam conditions."
    )

    return {
        "speaking_topics": out.get("speaking", state.get("speaking_topics", [])),
        "writing_topics": out.get("writing", state.get("writing_topics", [])),
        "reading_topics": out.get("reading", state.get("reading_topics", [])),
        "listening_topics": out.get("listening", state.get("listening_topics", [])),
        "study_plan_notes": study_plan,
        "status": "completed",
        "progress": 100.0,
    }
