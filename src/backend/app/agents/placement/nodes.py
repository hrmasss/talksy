"""Graph nodes for the IELTS placement test agent."""

from __future__ import annotations

import json
import re
from typing import Literal

from app.config import settings
from app.core.logging import logger
from langchain_core.messages import HumanMessage, SystemMessage

from ..common.llm import get_llm
from .models import PlacementEvaluation, PlacementQuestion
from .prompts import (
    get_placement_evaluation_prompt,
    get_placement_listening_prompt,
    get_placement_reading_prompt,
    get_placement_speaking_prompt,
    get_placement_writing_prompt,
)
from .state import (
    PLACEMENT_QUESTIONS_PER_SECTION,
    PLACEMENT_SECTIONS,
    PlacementState,
)


def _get_section_prompt(section: str, q_num: int, total: int) -> str:
    """Get the appropriate prompt for the current section."""
    if section == "listening":
        return get_placement_listening_prompt(q_num, total)
    elif section == "reading":
        return get_placement_reading_prompt(q_num, total)
    elif section == "writing":
        return get_placement_writing_prompt()
    elif section == "speaking":
        return get_placement_speaking_prompt(q_num, total)
    return ""


def _parse_json_from_text(text: str) -> dict:
    """Extract JSON from LLM response text."""
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        return json.loads(match.group())
    return {}


def _build_question_request(prompt: str) -> list[HumanMessage]:
    """Build a non-empty message payload for Gemini question generation."""
    cleaned_prompt = prompt.strip()
    if not cleaned_prompt:
        raise ValueError("Placement prompt must not be empty.")
    return [HumanMessage(content=cleaned_prompt)]


# ────────────────────────────────────────────────────────────────────
# 1. Initialise
# ────────────────────────────────────────────────────────────────────

async def initialise_placement_node(state: PlacementState) -> dict:
    """Set up the placement test."""
    logger.info("Initialising IELTS Placement Test")

    return {
        "current_section": "listening",
        "current_section_index": 0,
        "question_number": 0,
        "section_question_number": 0,
        "total_questions": sum(PLACEMENT_QUESTIONS_PER_SECTION.values()),
        "responses": [],
        "section_scores": {},
        "strengths": [],
        "weaknesses": [],
        "focus_areas": [],
        "current_options": [],
        "status": "in_progress",
    }


# ────────────────────────────────────────────────────────────────────
# 2. Generate Question
# ────────────────────────────────────────────────────────────────────

async def generate_placement_question_node(state: PlacementState) -> dict:
    """Generate the next placement test question."""
    section = state.get("current_section", "listening")
    section_q = state.get("section_question_number", 0) + 1
    total_for_section = PLACEMENT_QUESTIONS_PER_SECTION.get(section, 3)
    global_q = state.get("question_number", 0)

    prompt = _get_section_prompt(section, section_q, total_for_section)
    request_messages = _build_question_request(prompt)

    llm = get_llm(model=settings.gemini_model, temperature=0.8)

    try:
        structured = llm.with_structured_output(PlacementQuestion)
        q: PlacementQuestion = await structured.ainvoke(request_messages)
        q_data = q.model_dump()
    except Exception:
        raw = await llm.ainvoke(request_messages)
        q_data = _parse_json_from_text(raw.content)

    # Build question text with scenario/passage if present
    question_text = ""
    if q_data.get("scenario"):
        question_text = f"[Listening Scenario]\n{q_data['scenario']}\n\n"
    if q_data.get("passage"):
        question_text = f"[Reading Passage]\n{q_data['passage']}\n\n"
    question_text += q_data.get("question") or q_data.get("prompt", "")
    if q_data.get("instructions"):
        question_text += f"\n\n{q_data['instructions']}"

    options = q_data.get("options", [])
    q_type = q_data.get("question_type", "multiple_choice")

    logger.info("Placement Q{} [{}]: {}…", global_q + 1, section.upper(), question_text[:80])

    return {
        "messages": [SystemMessage(content=f"Generated {section} question {section_q}")],
        "current_question": question_text,
        "current_question_type": q_type,
        "current_options": options,
        "status": "awaiting_answer",
    }


# ────────────────────────────────────────────────────────────────────
# 3. Process Answer
# ────────────────────────────────────────────────────────────────────

async def process_placement_answer_node(state: PlacementState) -> dict:
    """Store the candidate's answer and advance counters."""
    answer = state.get("current_answer", "")
    question = state.get("current_question", "")
    section = state.get("current_section", "listening")
    q_type = state.get("current_question_type", "multiple_choice")
    global_q = state.get("question_number", 0)
    section_q = state.get("section_question_number", 0)
    section_idx = state.get("current_section_index", 0)

    responses = list(state.get("responses", []))
    responses.append({
        "section": section,
        "question": question,
        "answer": answer,
        "question_type": q_type,
        "question_number": global_q + 1,
    })

    # Advance counters
    new_section_q = section_q + 1
    new_global_q = global_q + 1
    new_section = section
    new_section_idx = section_idx

    total_for_section = PLACEMENT_QUESTIONS_PER_SECTION.get(section, 3)
    if new_section_q >= total_for_section:
        # Move to next section
        new_section_idx = section_idx + 1
        new_section_q = 0
        if new_section_idx < len(PLACEMENT_SECTIONS):
            new_section = PLACEMENT_SECTIONS[new_section_idx]

    logger.info("Recorded answer for Q{} [{}]", new_global_q, section)

    return {
        "responses": responses,
        "question_number": new_global_q,
        "section_question_number": new_section_q,
        "current_section": new_section,
        "current_section_index": new_section_idx,
        "current_answer": None,
        "messages": [HumanMessage(content=answer)],
    }


# ────────────────────────────────────────────────────────────────────
# 4. Final Evaluation
# ────────────────────────────────────────────────────────────────────

async def evaluate_placement_node(state: PlacementState) -> dict:
    """Evaluate all responses and produce the skill profile."""
    logger.info("Evaluating placement test responses")

    responses = state.get("responses", [])
    if not responses:
        return {
            "overall_band": 5.0,
            "section_scores": {"listening": 5.0, "reading": 5.0, "writing": 5.0, "speaking": 5.0},
            "status": "completed",
        }

    prompt = get_placement_evaluation_prompt(responses)
    llm = get_llm(model=settings.gemini_model, temperature=0.2)

    try:
        structured = llm.with_structured_output(PlacementEvaluation)
        evaluation: PlacementEvaluation = await structured.ainvoke(
            [HumanMessage(content=prompt)]
        )
        data = evaluation.model_dump()
    except Exception:
        try:
            raw = await llm.ainvoke([HumanMessage(content=prompt)])
            data = _parse_json_from_text(raw.content)
        except Exception:
            data = {
                "listening_band": 5.0,
                "reading_band": 5.0,
                "writing_band": 5.0,
                "speaking_band": 5.0,
                "overall_band": 5.0,
                "strengths": ["basic comprehension"],
                "weaknesses": ["needs further assessment"],
                "focus_areas": ["all sections"],
                "feedback_markdown": "# Placement Results\n\nEstimated Band: 5.0",
            }

    section_scores = {
        "listening": data.get("listening_band", 5.0),
        "reading": data.get("reading_band", 5.0),
        "writing": data.get("writing_band", 5.0),
        "speaking": data.get("speaking_band", 5.0),
    }

    overall = data.get("overall_band", 5.0)
    logger.info("Placement complete - Overall band: {}", overall)

    return {
        "section_scores": section_scores,
        "overall_band": overall,
        "strengths": data.get("strengths", []),
        "weaknesses": data.get("weaknesses", []),
        "focus_areas": data.get("focus_areas", []),
        "feedback_markdown": data.get("feedback_markdown", ""),
        "status": "completed",
    }


# ────────────────────────────────────────────────────────────────────
# 5. Routing
# ────────────────────────────────────────────────────────────────────

def route_after_placement_answer(state: PlacementState) -> Literal["next_question", "evaluate"]:
    """Decide whether to ask another question or evaluate."""
    total = state.get("total_questions", 9)
    answered = len(state.get("responses", []))

    if answered >= total:
        return "evaluate"
    return "next_question"
