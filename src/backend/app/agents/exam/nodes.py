"""Graph nodes for the IELTS exam agent."""

from __future__ import annotations

import json
import re
from typing import Literal

from app.config import settings
from app.memory.service import memory_service
from langchain_core.messages import HumanMessage, SystemMessage

from ..common.llm import get_llm
from .models import AnswerEvaluation, FinalExamReport
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

    print(f"🎓 Initialising IELTS {section.title()} exam - {difficulty} (target {target_band})")

    # ── Recall long-term memory for this user & section ──────────
    memory_context = ""
    if user_id:
        try:
            memory_context = await memory_service.recall_for_exam(
                user_id=user_id,
                section=section,
            )
        except Exception as exc:
            print(f"⚠️ Memory recall skipped: {exc}")
            memory_context = ""

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
            print(f"⚠️ Activity log skipped: {exc}")

    part = 1
    if section == "speaking":
        sys_prompt = get_speaking_examiner_prompt(
            difficulty_level=difficulty,
            target_band=target_band,
            total_questions=total_q,
            current_part=part,
            question_number=0,
        )
    elif section == "writing":
        sys_prompt = get_writing_examiner_prompt(
            difficulty_level=difficulty,
            target_band=target_band,
            task_number=1,
            exam_variant=variant,
        )
    else:
        # reading / listening
        if section == "reading":
            sys_prompt = get_reading_examiner_prompt(
                difficulty_level=difficulty,
                target_band=target_band,
                total_questions=total_q,
                question_number=0,
                exam_variant=variant,
            )
        else:
            sys_prompt = get_listening_examiner_prompt(
                difficulty_level=difficulty,
                target_band=target_band,
                total_questions=total_q,
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

    return {
        "messages": [SystemMessage(content=sys_prompt)],
        "target_band": target_band,
        "total_questions": total_q,
        "question_number": 0,
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
    """Ask the LLM to produce the next IELTS question."""
    section = state.get("exam_section", "speaking")
    qn = state.get("question_number", 0)
    total = state.get("total_questions", 8)
    target_band = state.get("target_band", "6.0-7.0")
    difficulty = state.get("difficulty_level", "intermediate")
    variant = state.get("exam_variant", "academic")

    if qn >= total:
        return {"should_continue": False}

    part = _current_part(state)

    # Build / refresh the system prompt for the current part
    if section == "speaking":
        sys_prompt = get_speaking_examiner_prompt(
            difficulty_level=difficulty,
            target_band=target_band,
            total_questions=total,
            current_part=part,
            question_number=qn,
        )
    elif section == "writing":
        task_num = 1 if qn == 0 else 2
        part = task_num
        sys_prompt = get_writing_examiner_prompt(
            difficulty_level=difficulty,
            target_band=target_band,
            task_number=task_num,
            exam_variant=variant,
        )
    else:
        if section == "reading":
            sys_prompt = get_reading_examiner_prompt(
                difficulty_level=difficulty,
                target_band=target_band,
                total_questions=total,
                question_number=qn,
                exam_variant=variant,
            )
        else:
            sys_prompt = get_listening_examiner_prompt(
                difficulty_level=difficulty,
                target_band=target_band,
                total_questions=total,
                question_number=qn,
            )

    llm = get_llm(model=settings.llm_model, temperature=0.8)

    # We keep full message history so the LLM avoids repeating topics
    messages = list(state.get("messages", []))

    # Inject an updated system message
    messages = [SystemMessage(content=sys_prompt)] + [
        m for m in messages if not isinstance(m, SystemMessage)
    ]

    response = await llm.ainvoke(messages)
    question_text = response.content.strip()

    # Determine question type
    q_type = "discussion"
    if section == "speaking":
        if part == 2:
            q_type = "cue_card"
        elif part == 1:
            q_type = "interview"
    elif section == "writing":
        q_type = f"task_{part}"

    # Determine phase
    if qn <= 1:
        phase = "warm_up"
    elif qn >= total - 2:
        phase = "wrap_up"
    else:
        phase = "main"

    questions_asked = list(state.get("questions_asked", []))
    questions_asked.append({
        "number": qn + 1,
        "part": part,
        "type": q_type,
        "text": question_text,
    })

    print(f"❓ Q{qn+1}/{total} [Part {part}] {q_type}: {question_text[:80]}…")

    return {
        "messages": [response],
        "current_question": question_text,
        "current_question_type": q_type,
        "current_part": part,
        "current_phase": phase,
        "questions_asked": questions_asked,
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
        print("⚠️ No answer provided")
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

    llm = get_llm(model=settings.llm_model, temperature=0.3)

    try:
        structured = llm.with_structured_output(AnswerEvaluation)
        evaluation: AnswerEvaluation = await structured.ainvoke(
            [HumanMessage(content=eval_prompt)]
        )
        eval_data = evaluation.model_dump()
        eval_data["question_number"] = last["question_number"]
    except Exception as exc:
        print(f"⚠️ Structured eval failed: {exc}")
        # Fallback: try raw JSON parse
        try:
            raw = await llm.ainvoke([HumanMessage(content=eval_prompt)])
            match = re.search(r"\{.*\}", raw.content, re.DOTALL)
            eval_data = json.loads(match.group()) if match else {"band_score": 5.0}
        except Exception:
            eval_data = {"band_score": 5.0, "feedback": "Evaluation failed"}

    score = eval_data.get("band_score", 5.0)
    last["evaluation"] = eval_data

    scores = list(state.get("performance_scores", []))
    scores.append(score)

    avg = sum(scores) / len(scores)
    print(f"📊 Q{last['question_number']} band: {score} (avg so far: {avg:.1f})")

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
    print("🎯 Running final IELTS evaluation …")

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

    llm = get_llm(model=settings.llm_model, temperature=0.2)

    try:
        structured = llm.with_structured_output(FinalExamReport)
        report: FinalExamReport = await structured.ainvoke(
            [HumanMessage(content=prompt)]
        )
        data = report.model_dump()
    except Exception as exc:
        print(f"⚠️ Structured final eval failed: {exc}, trying raw …")
        try:
            raw = await llm.ainvoke([HumanMessage(content=prompt)])
            match = re.search(r"\{.*\}", raw.content, re.DOTALL)
            data = json.loads(match.group()) if match else {}
        except Exception:
            scores = state.get("performance_scores", [])
            avg = sum(scores) / len(scores) if scores else 5.0
            data = {
                "overall_band": round(avg * 2) / 2,
                "final_report_markdown": "Evaluation completed. Check individual scores.",
            }

    overall = data.get("overall_band", 5.0)
    report_md = data.get("final_report_markdown", "")

    # Merge individual evaluations back into candidate_answers
    for ev in data.get("individual_evaluations", []):
        idx = ev.get("question_number", 0) - 1
        if 0 <= idx < len(answers):
            answers[idx]["evaluation"] = ev

    print(f"✅ Final band score: {overall}")

    # ── Persist to long-term memory ──────────────────────────────
    user_id = state.get("user_id", "")
    if user_id:
        try:
            await memory_service.store_exam_result(
                user_id=user_id,
                section=section,
                band_score=overall,
                strengths=data.get("strengths"),
                weaknesses=data.get("weaknesses"),
                recommendations=data.get("recommendations"),
                report_summary=report_md[:500] if report_md else "",
                extra_metadata={
                    "difficulty": difficulty,
                    "target_band": target_band,
                    "total_questions": len(answers),
                },
            )
        except Exception as exc:
            print(f"⚠️ Memory store after exam failed: {exc}")

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
