"""Prompts for daily study content generation."""

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

    return f"""You are an expert IELTS tutor creating a personalized IELTS daily study plan.

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
1. This is a PRACTICE phase, not an evaluation phase. Do not ask the student to take a test.
2. Allocate MORE support to weak areas, especially {weakest_section}.
3. Use clear instructions and encouraging language, but match the intellectual level to the student's band.
4. Activities must match the student's current level and stretch them toward band {target_band}. Do not default to beginner material unless the current band is genuinely low.
5. Total activities should fill approximately {practice_time_minutes} minutes.
6. Every activity must be fully self-contained and easy to complete on a study site.
7. Keep materials readable on screen: short sections, bullets, and practical examples.
8. Avoid advanced jargon unless you explain it clearly.
9. Make the plan challenging but realistic for the student's level.
10. Avoid childish or extremely basic content such as matching words like apple, dog, car, or house to obvious meanings.
11. Vocabulary tasks must focus on higher-value IELTS vocabulary: collocations, paraphrasing, context meaning, register, word choice, or sentence completion.
12. Reading and listening tasks should usually require understanding, inference, detail selection, paraphrase recognition, or main-idea tracking rather than only recall of one obvious fact.
13. Writing tasks should require a developed response, not only one simple sentence, unless the student's current band is below 4.5.
14. Speaking tasks should push the learner to answer with developed ideas and examples, not only name/basic-introduction prompts, unless the student's current band is below 4.5.

Generate EXACTLY 5 activities in this EXACT order:
1. section="vocabulary", activity_type="vocabulary_practice", title="Vocabulary in Context"
2. section="listening", activity_type="mini_listening", title="Targeted Listening Drill"
3. section="reading", activity_type="reading_passage", title="Analytical Reading Passage"
4. section="writing", activity_type="writing_task", title="Focused Writing Task"
5. section="speaking", activity_type="speaking_prompt", title="Speaking Extension Prompt"

Each activity must include practical details using this student-friendly content structure:
- "overview": one short supportive sentence explaining the activity
- "instructions": 2-4 short action steps
- "study_goal": one sentence about what skill this builds
- "warm_up": optional short starter or reminder
- "material_title": short title for the study material
- "material": the full exercise content
- "vocabulary": optional array of objects with "word", "meaning", and "example"
- "questions": optional array of objects with "prompt" and "answer_hint"
- "sentence_frames": optional array of simple model sentence starters
- "checkpoints": optional array of small things to remember while doing the task
- "sample_response": optional short sample answer
- "study_tip": one practical tip
- "next_step": one small follow-up action after finishing

Respond with a JSON object:
{{
    "rationale": "Start with: These activities were chosen to address the student's weaknesses, focusing on improving listening and reading comprehension, and developing writing and speaking skills, with a strong emphasis on vocabulary building. Given the student's current estimated band of {current_band:.1f} and target band of {target_band:.1f}, activities are designed to be foundational, gradually increasing in difficulty.",
    "activities": [
        {{
            "section": "Use the exact required section",
            "activity_type": "Use the exact required activity_type",
            "title": "Use the exact required title",
            "difficulty_level": 1-5,
            "estimated_minutes": <int>,
            "content": {{
                "overview": "Short explanation...",
                "instructions": ["Step 1...", "Step 2..."],
                "study_goal": "What this helps the student improve",
                "warm_up": "Optional starter",
                "material_title": "Clear label",
                "material": "The actual content the learner should study",
                "vocabulary": [
                    {{"word": "example", "meaning": "simple meaning", "example": "Example sentence."}}
                ],
                "questions": [
                    {{"prompt": "Question text", "answer_hint": "Short hint"}}
                ],
                "sentence_frames": ["I usually...", "I want to..."],
                "checkpoints": ["Remember ...", "Check ..."],
                "sample_response": "Optional simple model answer",
                "study_tip": "Helpful tip...",
                "next_step": "Tiny follow-up task"
            }}
        }}
    ]
}}"""
