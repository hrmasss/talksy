"""Prompts for daily study content generation and activity evaluation."""

from __future__ import annotations

from typing import Any


def get_daily_study_plan_prompt(
    *,
    current_band: float,
    target_band: float,
    strengths: list[str],
    weaknesses: list[str],
    focus_areas: list[str],
    section_scores: dict[str, float],
    recent_history: list[dict[str, Any]],
    practice_time_minutes: int,
) -> str:
    """Prompt for generating a personalized daily study plan."""

    if not isinstance(section_scores, dict):
        section_scores = {}

    safe_section_scores: dict[str, float | str] = {}
    for key in ("listening", "reading", "writing", "speaking"):
        raw = section_scores.get(key)
        if raw is None:
            continue
        try:
            safe_section_scores[key] = float(raw)
        except (TypeError, ValueError):
            continue

    history_text = ""
    if recent_history:
        for i, h in enumerate(recent_history[-5:], 1):
            history_text += f"  {i}. {h.get('section', '?')} - Band {h.get('band_score', '?')} ({h.get('date', '?')})\n"
    else:
        history_text = "  No recent test history.\n"

    weakest_section = min(safe_section_scores, key=safe_section_scores.get) if safe_section_scores else "writing"
    band_gap = target_band - current_band

    return f"""You are an expert IELTS tutor creating a personalized daily study plan.

STUDENT PROFILE:
- Current Estimated Band: {current_band}
- Target Band: {target_band}
- Band Gap: {band_gap:.1f}
- Available Practice Time: {practice_time_minutes} minutes

SECTION SCORES:
        - Listening: {safe_section_scores.get('listening', 'N/A')}
        - Reading: {safe_section_scores.get('reading', 'N/A')}
        - Writing: {safe_section_scores.get('writing', 'N/A')}
        - Speaking: {safe_section_scores.get('speaking', 'N/A')}

STRENGTHS: {', '.join(strengths) if strengths else 'Not yet assessed'}
WEAKNESSES: {', '.join(weaknesses) if weaknesses else 'Not yet assessed'}
FOCUS AREAS: {', '.join(focus_areas) if focus_areas else 'All sections'}
WEAKEST SECTION: {weakest_section}

RECENT HISTORY:
{history_text}

GENERATION RULES:
1. Allocate MORE time to weak areas (especially {weakest_section})
2. Include a mix of activity types for variety
3. Gradually increase difficulty toward target band {target_band}
4. Total activities should fill approximately {practice_time_minutes} minutes
5. Each activity should be self-contained and completable independently
6. Include at least one vocabulary exercise daily
7. Focus writing/speaking activities on the student's specific weaknesses

Generate 4-6 study activities. Each activity must be COMPLETE - include all content
needed to do the exercise (passage text, questions, word lists, prompts, etc.).

Respond with a JSON object:
{{
    "rationale": "Brief explanation of why these activities were chosen...",
    "activities": [
        {{
            "section": "vocabulary|listening|reading|writing|speaking",
            "activity_type": "vocabulary_practice|mini_listening|reading_passage|writing_task|speaking_prompt",
            "title": "Short descriptive title",
            "difficulty_level": 1-5,
            "estimated_minutes": <int>,
            "content": {{
                "instructions": "What to do...",
                "material": "The actual content (passage, word list, scenario, prompt, etc.)",
                "questions": ["Q1...", "Q2..."],
                "options": {{}},
                "correct_answers": {{}},
                "tips": "Optional study tip..."
            }}
        }}
    ]
}}"""


def get_activity_evaluation_prompt(
    *,
    section: str,
    activity_type: str,
    content: dict[str, Any],
    user_response: str,
) -> str:
    """Evaluate a user's response to a study activity."""

    return f"""You are an IELTS examiner evaluating a student's response to a study activity.

ACTIVITY DETAILS:
- Section: {section}
- Type: {activity_type}
- Instructions: {content.get('instructions', '')}
- Material: {str(content.get('material', ''))[:500]}
- Questions: {content.get('questions', [])}

STUDENT'S RESPONSE:
{user_response}

{"CORRECT ANSWERS: " + str(content.get('correct_answers', '')) if content.get('correct_answers') else ''}

EVALUATION TASK:
1. Assess the response quality using IELTS band descriptors
2. For objective questions: check correctness
3. For writing/speaking: evaluate grammar, vocabulary, coherence, task achievement
4. Provide constructive feedback and specific improvement suggestions

Respond with a JSON object:
{{
    "band_score": <float 0-9>,
    "is_correct": <bool or null for subjective>,
    "feedback": "Detailed feedback...",
    "grammar_notes": "Specific grammar observations...",
    "vocabulary_notes": "Vocabulary assessment...",
    "strengths": ["..."],
    "weaknesses": ["..."],
    "suggestions": ["Specific improvement tip 1", "Specific improvement tip 2"],
    "corrected_version": "If applicable, show the corrected/improved version..."
}}"""
