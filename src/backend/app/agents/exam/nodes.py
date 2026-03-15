"""Graph nodes for the IELTS exam agent."""

from __future__ import annotations

import asyncio
from typing import Literal

from app.config import settings
from app.core.logging import logger
from app.memory.service import memory_service
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from ..common.llm import get_llm
from .models import AnswerEvaluation, ExamQuestion, FinalExamReport
from .prompts import (
    get_answer_evaluation_prompt,
    get_final_evaluation_prompt,
    get_listening_examiner_prompt,
    get_reading_examiner_prompt,
    get_speaking_examiner_prompt,
    get_user_history_context,
    get_writing_examiner_prompt,
)
from .state import (
    ExamState,
    get_difficulty_info,
)

# ============================================================================
# Helpers
# ============================================================================

def _current_part(state: ExamState) -> int:
    """Determine which IELTS part we're in based on question number."""
    section = state.get("exam_section", "speaking")
    qn = state.get("question_number", 0)

    if section == "speaking":
        if qn < 4:
            return 1
        elif qn < 5:
            return 2
        else:
            return 3
    elif section == "writing":
        return 1 if qn < 1 else 2
    return 1


def _content_to_text(content: object) -> str:
    """Normalize LangChain model content payloads to plain text.

    Some providers return a list of blocks instead of a raw string.
    """
    if isinstance(content, str):
        return content.strip()

    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, str):
                text = item.strip()
                if text:
                    parts.append(text)
                continue

            if isinstance(item, dict):
                # Gemini / LangChain content blocks often expose text in one of
                # these keys.
                for key in ("text", "content", "value"):
                    raw = item.get(key)
                    if isinstance(raw, str):
                        text = raw.strip()
                        if text:
                            parts.append(text)
                        break

        return "\n".join(parts).strip()

    if isinstance(content, dict):
        for key in ("text", "content", "value"):
            raw = content.get(key)
            if isinstance(raw, str) and raw.strip():
                return raw.strip()

    return str(content).strip()


def _part_for_question(section: str, question_number: int) -> int:
    """Determine IELTS part/task number for a zero-based question index."""
    if section == "speaking":
        if question_number < 4:
            return 1
        if question_number < 5:
            return 2
        return 3
    if section == "writing":
        return 1 if question_number < 1 else 2
    return 1


def _default_question_type(section: str, part: int) -> str:
    """Return a sane default question type based on section and part."""
    if section == "speaking":
        if part == 1:
            return "interview"
        if part == 2:
            return "cue_card"
        return "discussion"
    if section == "writing":
        return f"task_{part}"
    return "discussion"


def _system_prompt_for_question(
    *,
    section: str,
    difficulty: str,
    target_band: str,
    total_questions: int,
    exam_variant: str,
    question_number: int,
) -> str:
    """Build section-specific examiner prompt for one specific question."""
    part = _part_for_question(section, question_number)
    if section == "speaking":
        return get_speaking_examiner_prompt(
            difficulty_level=difficulty,
            target_band=target_band,
            total_questions=total_questions,
            current_part=part,
            question_number=question_number,
        )
    if section == "writing":
        return get_writing_examiner_prompt(
            difficulty_level=difficulty,
            target_band=target_band,
            task_number=part,
            exam_variant=exam_variant,
        )
    if section == "reading":
        return get_reading_examiner_prompt(
            difficulty_level=difficulty,
            target_band=target_band,
            total_questions=total_questions,
            question_number=question_number,
            exam_variant=exam_variant,
        )
    return get_listening_examiner_prompt(
        difficulty_level=difficulty,
        target_band=target_band,
        total_questions=total_questions,
        question_number=question_number,
    )


async def _generate_structured_question(
    *,
    section: str,
    difficulty: str,
    target_band: str,
    total_questions: int,
    exam_variant: str,
    question_number: int,
) -> dict:
    """Generate one exam question using strict structured output."""
    part = _part_for_question(section, question_number)
    sys_prompt = _system_prompt_for_question(
        section=section,
        difficulty=difficulty,
        target_band=target_band,
        total_questions=total_questions,
        exam_variant=exam_variant,
        question_number=question_number,
    )

    llm = get_llm(model=settings.gemini_model, temperature=0.8)
    structured = llm.with_structured_output(ExamQuestion)
    user_prompt = (
        f"Generate ONLY question #{question_number + 1} of {total_questions} for IELTS {section}. "
        "Return exactly one structured question object. Keep wording concise, natural, "
        "and appropriate for the requested level and target band."
    )
    question: ExamQuestion = await structured.ainvoke(
        [
            SystemMessage(content=sys_prompt),
            HumanMessage(content=user_prompt),
        ]
    )
    data = question.model_dump()

    question_type = data.get("question_type") or _default_question_type(section, part)
    return {
        "number": question_number + 1,
        "part": part,
        "type": question_type,
        "text": data.get("question_text", "").strip(),
        "options": data.get("options") or [],
        "time_limit_seconds": data.get("time_limit_seconds"),
        "cue_card": data.get("cue_card"),
        "scoring_notes": data.get("scoring_notes"),
    }


# ============================================================================
# 1. Initialise Exam
# ============================================================================

async def initialise_exam_node(state: ExamState) -> dict:
    """Set up the exam session - build the system prompt and initialise state."""
    section = state.get("exam_section", "speaking")
    difficulty = state.get("difficulty_level", "intermediate")
    diff_info = get_difficulty_info(difficulty)
    target_band = state.get("target_band") or diff_info["target_band"]
    total_q = state.get("total_questions") or diff_info["total_questions"]
    variant = state.get("exam_variant", "academic")
    user_id = state.get("user_id", "")

    logger.info(
        "Initialising IELTS {} exam - {} (target {})",
        section.title(), difficulty, target_band,
    )

    # Recall long-term memory for this user & section
    memory_context = ""
    recent_exam_results_context = ""
    if user_id:
        try:
            memory_context = await memory_service.recall_for_exam(
                user_id=user_id,
                section=section,
            )
        except Exception as exc:
            logger.warning("Memory recall skipped: {}", exc)
            memory_context = ""

        try:
            recent_exam_results_context = await memory_service.build_recent_exam_results_context(
                user_id=user_id,
                section=section,
                limit=5,
            )
        except Exception as exc:
            logger.warning("Recent exam memory fetch skipped: {}", exc)
            recent_exam_results_context = ""

        # Log exam start as user activity
        try:
            await memory_service.store_user_activity(
                user_id=user_id,
                action="exam_started",
                detail=(
                    f"Started {section} exam, "
                    f"difficulty={difficulty}, target_band={target_band}"
                ),
                metadata={
                    "section": section,
                    "difficulty": difficulty,
                    "target_band": target_band,
                },
            )
        except Exception as exc:
            logger.warning("Activity log skipped: {}", exc)

    part = 1
    sys_prompt = _system_prompt_for_question(
        section=section,
        difficulty=difficulty,
        target_band=target_band,
        total_questions=total_q,
        exam_variant=variant,
        question_number=0,
    )

    # Append user memory context so the LLM can personalise
    if memory_context:
        sys_prompt += (
            "\n\n--- USER HISTORY (from long-term memory) ---\n"
            f"{memory_context}\n"
            "Use the above context to tailor questions to the user's level, "
            "focus on their weak areas, and avoid repeating topics they've "
            "already mastered.\n"
        )

    if recent_exam_results_context:
        sys_prompt += (
            "\n\n--- RECENT EXAM RESULTS (TOP 5, SAME SECTION) ---\n"
            f"{recent_exam_results_context}\n"
            "Generate new questions based on these past results: reinforce weak "
            "areas, gradually increase challenge, and avoid repeating recently "
            "used prompts.\n"
        )

    # Generate all exam questions up front so gameplay can return one-by-one
    # without per-question LLM latency.
    max_parallel = max(1, min(6, int(total_q)))
    semaphore = asyncio.Semaphore(max_parallel)

    async def _generate_one(question_number: int) -> dict:
        async with semaphore:
            try:
                return await _generate_structured_question(
                    section=section,
                    difficulty=difficulty,
                    target_band=str(target_band),
                    total_questions=int(total_q),
                    exam_variant=variant,
                    question_number=question_number,
                )
            except Exception as exc:
                logger.warning(
                    "Question pre-generation failed for Q{}: {}",
                    question_number + 1,
                    exc,
                )
                fallback_part = _part_for_question(section, question_number)
                return {
                    "number": question_number + 1,
                    "part": fallback_part,
                    "type": _default_question_type(section, fallback_part),
                    "text": f"Please answer IELTS {section} question {question_number + 1}.",
                    "options": [],
                    "time_limit_seconds": None,
                    "cue_card": None,
                    "scoring_notes": None,
                }

    question_bank = await asyncio.gather(
        *(_generate_one(i) for i in range(int(total_q)))
    )

    return {
        "messages": [SystemMessage(content=sys_prompt)],
        "target_band": target_band,
        "total_questions": total_q,
        "question_number": 0,
        "question_bank": question_bank,
        "questions_asked": [],
        "candidate_answers": [],
        "performance_scores": [],
        "current_part": part,
        "current_phase": "warm_up",
        "should_continue": True,
        "status": "in_progress",
    }


# ============================================================================
# 2. Generate Question
# ============================================================================

async def generate_question_node(state: ExamState) -> dict:
    """Set the next question from the pre-generated question bank."""
    section = state.get("exam_section", "speaking")
    qn = state.get("question_number", 0)
    total = state.get("total_questions", 8)

    if qn >= total:
        return {"should_continue": False}

    question_bank = state.get("question_bank", [])
    selected = question_bank[qn] if qn < len(question_bank) else None

    part = selected.get("part") if selected else _current_part(state)
    question_text = (selected or {}).get("text") or ""
    q_type = (selected or {}).get("type") or _default_question_type(section, part)

    # Determine phase
    if qn <= 1:
        phase = "warm_up"
    elif qn >= total - 2:
        phase = "wrap_up"
    else:
        phase = "main"

    questions_asked = list(state.get("questions_asked", []))
    question_data = {
        "number": qn + 1,
        "part": part,
        "type": q_type,
        "text": question_text,
        "options": (selected or {}).get("options", []),
        "time_limit_seconds": (selected or {}).get("time_limit_seconds"),
        "cue_card": (selected or {}).get("cue_card"),
    }
    questions_asked.append(question_data)

    logger.info("Q{}/{} [Part {}] {}: {}...", qn + 1, total, part, q_type, question_text[:80])

    return {
        "messages": [AIMessage(content=question_text)],
        "current_question": question_text,
        "current_question_type": q_type,
        "current_part": part,
        "current_phase": phase,
        "questions_asked": questions_asked,
        "current_question_options": question_data.get("options", []),
        "current_question_time_limit_seconds": question_data.get("time_limit_seconds"),
        "should_continue": True,
    }


# ============================================================================
# 3. Process Answer
# ============================================================================

async def process_answer_node(state: ExamState) -> dict:
    """Store the candidate's answer and update bookkeeping."""
    answer = state.get("current_answer", "")
    question = state.get("current_question", "")
    qn = state.get("question_number", 0)
    part = state.get("current_part", 1)
    q_type = state.get("current_question_type", "unknown")

    if not answer:
        logger.warning("No answer provided")
        return {}

    candidate_answers = list(state.get("candidate_answers", []))
    record = {
        "question": question,
        "answer": answer,
        "part": part,
        "question_type": q_type,
        "question_number": qn + 1,
        "evaluation": None,
    }
    candidate_answers.append(record)

    return {
        "candidate_answers": candidate_answers,
        "question_number": qn + 1,
        "current_answer": None,
        "messages": [HumanMessage(content=answer)],
    }


# ============================================================================
# 4. Evaluate Answer (quick per-question)
# ============================================================================

async def evaluate_answer_node(state: ExamState) -> dict:
    """Quick evaluation of the last answer to track performance."""
    answers = state.get("candidate_answers", [])
    if not answers:
        return {}

    last = answers[-1]
    section = state.get("exam_section", "speaking")
    target_band = state.get("target_band", "6.0-7.0")

    eval_prompt = get_answer_evaluation_prompt(
        section=section,
        part=last.get("part", 1),
        question=last["question"],
        answer=last["answer"],
        target_band=target_band,
    )

    llm = get_llm(model=settings.gemini_model, temperature=0.3)

    try:
        structured = llm.with_structured_output(AnswerEvaluation)
        evaluation: AnswerEvaluation = await structured.ainvoke(
            [HumanMessage(content=eval_prompt)]
        )
        eval_data = evaluation.model_dump()
        eval_data["question_number"] = last["question_number"]
    except Exception as exc:
        logger.warning("Structured eval failed: {}", exc)
        fallback = AnswerEvaluation(
            question_number=last["question_number"],
            band_score=5.0,
            task_achievement=5.0,
            coherence_cohesion=5.0,
            lexical_resource=5.0,
            grammatical_range=5.0,
            pronunciation=5.0 if section == "speaking" else None,
            strengths=[],
            weaknesses=["Could not evaluate automatically"],
            suggestions=["Retry answer evaluation"],
            feedback="Evaluation failed. A default score was assigned.",
        )
        eval_data = fallback.model_dump()

    score = eval_data.get("band_score", 5.0)
    last["evaluation"] = eval_data

    scores = list(state.get("performance_scores", []))
    scores.append(score)

    avg = sum(scores) / len(scores)
    logger.info("Q{} band: {} (avg so far: {:.1f})", last["question_number"], score, avg)

    return {
        "candidate_answers": answers,
        "performance_scores": scores,
        "current_evaluation": eval_data,
    }


# ============================================================================
# 5. Final Evaluation
# ============================================================================

async def final_evaluation_node(state: ExamState) -> dict:
    """Comprehensive evaluation of the entire exam session."""
    logger.info("Running final IELTS evaluation")

    section = state.get("exam_section", "speaking")
    answers = state.get("candidate_answers", [])
    target_band = state.get("target_band", "6.0-7.0")
    difficulty = state.get("difficulty_level", "intermediate")

    if not answers:
        return {
            "final_band_score": 0.0,
            "final_report": "No answers to evaluate.",
            "status": "completed",
        }

    prompt = get_final_evaluation_prompt(
        section=section,
        candidate_answers=answers,
        target_band=target_band,
        difficulty_level=difficulty,
    )

    llm = get_llm(model=settings.gemini_model, temperature=0.2)

    try:
        structured = llm.with_structured_output(FinalExamReport)
        report: FinalExamReport = await structured.ainvoke(
            [HumanMessage(content=prompt)]
        )
        data = report.model_dump()
    except Exception as exc:
        logger.warning("Structured final eval failed: {}", exc)
        scores = state.get("performance_scores", [])
        avg = sum(scores) / len(scores) if scores else 5.0
        fallback_report = FinalExamReport(
            individual_evaluations=[],
            section_scores=[],
            overall_band=round(avg * 2) / 2,
            strengths=[],
            weaknesses=["Could not generate final structured evaluation"],
            recommendations=["Retry final evaluation"],
            final_report_markdown="Evaluation completed with fallback scoring.",
        )
        data = fallback_report.model_dump()

    overall = data.get("overall_band", 5.0)
    report_md = data.get("final_report_markdown", "")

    # Merge individual evaluations back into candidate_answers
    for ev in data.get("individual_evaluations", []):
        idx = ev.get("question_number", 0) - 1
        if 0 <= idx < len(answers):
            answers[idx]["evaluation"] = ev

    logger.info("Final band score: {}", overall)

    # Exam result persistence to long-term memory is scheduled in the API layer
    # as a background task to avoid blocking the response.

    return {
        "candidate_answers": answers,
        "final_band_score": overall,
        "final_report": report_md,
        "status": "completed",
        "should_continue": False,
    }


# ============================================================================
# 6. Routing helpers
# ============================================================================

def route_after_answer(state: ExamState) -> Literal["evaluate", "final"]:
    """After processing an answer, decide whether to evaluate or finish."""
    total = state.get("total_questions", 8)
    answered = len(state.get("candidate_answers", []))

    if answered >= total:
        return "final"
    return "evaluate"


def route_after_evaluation(state: ExamState) -> Literal["next_question", "final"]:
    """After evaluating, decide whether to ask another question or wrap up."""
    total = state.get("total_questions", 8)
    answered = len(state.get("candidate_answers", []))

    if answered >= total:
        return "final"
    return "next_question"
