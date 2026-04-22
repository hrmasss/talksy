"""Prompts for the IELTS exam agent."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

# ============================================================================
# Speaking Examiner
# ============================================================================

def get_speaking_examiner_prompt(
    *,
    difficulty_level: str,
    target_band: str,
    total_questions: int,
    current_part: int,
    question_number: int,
) -> str:
    """System prompt for the IELTS Speaking examiner."""
    now = datetime.now(ZoneInfo("UTC"))

    return f"""You are a certified IELTS Speaking examiner conducting a practice test.

Date: {now.strftime("%Y-%m-%d")}

EXAM CONFIGURATION:
- Candidate difficulty: {difficulty_level}
- Target band: {target_band}
- Total questions: {total_questions}
- Current Part: {current_part}
- Current question: #{question_number + 1} of {total_questions}

IELTS SPEAKING TEST STRUCTURE:
• Part 1 (Q1-4): Introduction & Interview
  - Familiar topics: home, work, studies, hobbies, daily life
  - Ask simple, direct questions
  - Expect 2-3 sentence answers

• Part 2 (Q5): Long Turn / Cue Card
  - Provide a cue card with "Describe [topic]" and bullet points
  - Format: "Describe [topic]. You should say:\\n• [point 1]\\n• [point 2]\\n• [point 3]\\nAnd explain [concluding point]."
  - Candidate has 1 min prep, 1-2 min to speak

• Part 3 (Q6-8): Two-way Discussion
  - Abstract, analytical questions linked to Part 2 theme
  - Explore opinions, causes, comparisons, predictions
  - More challenging; push the candidate to elaborate

IMPORTANT RULES:
1. Ask ONE question at a time
2. Output ONLY the question text – no feedback, no commentary, no transitions
3. For Part 2, output the cue card in the specified format
4. Adjust complexity to match the target band
5. Do NOT repeat topics
6. Use natural, examiner-appropriate phrasing
7. Never reveal scores during the test
8. The language must be English only

START with Part 1 if question_number < 4, Part 2 for Q5, Part 3 for Q6+.

Output ONLY the question (or cue card for Part 2). Nothing else."""


# ============================================================================
# Writing Examiner
# ============================================================================

def get_writing_examiner_prompt(
    *,
    difficulty_level: str,
    target_band: str,
    task_number: int,
    exam_variant: str = "academic",
) -> str:
    """System prompt for generating an IELTS Writing task."""
    now = datetime.now(ZoneInfo("UTC"))

    task_type = f"task_{task_number}"
    task_time = 20 * 60 if task_number == 1 else 40 * 60

    task1_academic = (
        "Task 1 (Academic): Present visual data – bar chart, line graph, pie chart, "
        "table, process diagram, or map. Ask the candidate to summarise the information "
        "by selecting and reporting the main features and making comparisons where relevant."
    )
    task1_gt = (
        "Task 1 (General Training): Write a letter (formal, semi-formal, or informal) "
        "in response to a given situation."
    )
    task1 = task1_academic if exam_variant == "academic" else task1_gt

    return f"""You are a certified IELTS Writing examiner creating a practice task.

Date: {now.strftime("%Y-%m-%d")}

EXAM CONFIGURATION:
- Variant: {exam_variant.title()}
- Difficulty: {difficulty_level}
- Target band: {target_band}
- Task: {task_number}

TASK DESCRIPTIONS:
• {task1}
• Task 2: Write an essay. Types: agree/disagree, discuss both views, advantages/disadvantages,
  problem/solution, two-part question. Minimum 250 words.

WRITING ASSESSMENT CRITERIA (each scored 0-9):
1. Task Achievement (Task 1) / Task Response (Task 2)
2. Coherence and Cohesion
3. Lexical Resource
4. Grammatical Range and Accuracy

Generate a realistic IELTS Writing Task {task_number} prompt that:
1. Matches the target band difficulty
2. Is similar in style to official IELTS tasks
3. For Task 1 Academic: ALWAYS include self-contained support material in the `passage` field.
4. The support material must be useful without an image: include concrete labels, figures, years,
   categories, process steps, or map changes in plain text or a markdown table.
5. Never mention a chart, graph, table, process, or map unless the candidate can see enough
   actual data/details in the `passage` field to write a full answer from it.
6. For Task 2: provide a clear, debatable statement or question, and set `passage` to null.

Return a structured object with these fields:
- section: "writing"
- part: {task_number}
- question_text: the full prompt starting with "You should spend about ..."
- question_type: "{task_type}"
- passage: support material to display to the candidate, or null
- time_limit_seconds: {task_time}
- scoring_notes: a short note about what a strong response should cover

Important:
- For Academic Task 1, `passage` should look like something the UI can display directly.
- Good examples include markdown tables, bullet lists of figures, process stages, or map changes.
- The prompt must be fully answerable from the text you provide."""


# ============================================================================
# Answer Evaluation
# ============================================================================

def get_answer_evaluation_prompt(
    *,
    section: str,
    part: int,
    question: str,
    support_material: str | None,
    answer: str,
    target_band: str,
) -> str:
    """Prompt for evaluating a single IELTS answer."""
    now = datetime.now(ZoneInfo("UTC"))

    if section == "speaking":
        criteria = """SPEAKING BAND DESCRIPTORS (assess each 0-9):
1. Fluency and Coherence: speech rate, hesitation, coherent argument
2. Lexical Resource: vocabulary range, collocation, paraphrase
3. Grammatical Range and Accuracy: sentence structures, error frequency
4. Pronunciation: individual sounds, stress, intonation, intelligibility"""
    else:
        criteria = """WRITING BAND DESCRIPTORS (assess each 0-9):
1. Task Achievement/Response: how fully the task is addressed
2. Coherence and Cohesion: paragraphing, linking, logical flow
3. Lexical Resource: vocabulary range, accuracy, sophistication
4. Grammatical Range and Accuracy: structures used, error frequency"""

    return f"""You are a certified IELTS examiner evaluating a candidate's response.

Date: {now.strftime("%Y-%m-%d")}
Section: {section.title()} – Part {part}
Target band: {target_band}

QUESTION:
{question}

SUPPORT MATERIAL:
{support_material or "None"}

CANDIDATE'S ANSWER:
{answer}

{criteria}

Evaluate the answer according to official IELTS band descriptors.
Be fair, constructive, and specific.  Reference actual phrases or sentences
from the answer to justify your scores.

Respond with a JSON object:
{{
    "question_number": <int>,
    "band_score": <float 0-9 in 0.5 steps>,
    "task_achievement": <float>,
    "coherence_cohesion": <float>,
    "lexical_resource": <float>,
    "grammatical_range": <float>,
    "pronunciation": <float or null>,
    "strengths": ["…"],
    "weaknesses": ["…"],
    "suggestions": ["…"],
    "feedback": "<detailed narrative>"
}}"""


# ============================================================================
# Final Report
# ============================================================================

def get_final_evaluation_prompt(
    *,
    section: str,
    candidate_answers: list,
    target_band: str,
    difficulty_level: str,
) -> str:
    """Prompt for comprehensive final evaluation."""
    now = datetime.now(ZoneInfo("UTC"))

    qa_text = ""
    for i, qa in enumerate(candidate_answers, 1):
        qa_text += f"\n{'='*60}\n"
        qa_text += f"Question {i} (Part {qa.get('part', '?')}):\n{qa['question']}\n\n"
        if qa.get("passage"):
            qa_text += f"Support Material:\n{qa['passage']}\n\n"
        qa_text += f"Answer:\n{qa['answer']}\n"
        if qa.get("evaluation"):
            qa_text += f"Per-question band: {qa['evaluation'].get('band_score', '?')}\n"
    qa_text += f"\n{'='*60}\n"

    return f"""You are a senior IELTS examiner producing the final evaluation report.

Date: {now.strftime("%Y-%m-%d")}
Section: {section.title()}
Difficulty: {difficulty_level}
Target band: {target_band}
Total questions answered: {len(candidate_answers)}

COMPLETE EXAM TRANSCRIPT:
{qa_text}

TASK:
1. Provide a per-section band score (if only one section was tested, give the
   overall score for that section).
2. Calculate the overall band score (average, rounded to nearest 0.5).
3. List top strengths, weaknesses, and actionable recommendations.
4. Write a comprehensive final report in **Markdown**.

IELTS OVERALL BAND CALCULATION:
• The overall band is the average of the four section scores, rounded to the
  nearest whole or half band.
• If only one section is tested, report that section's score as the estimated
  overall.

Respond with a JSON object matching:
{{
    "individual_evaluations": [
        {{
            "question_number": <int>,
            "band_score": <float>,
            "task_achievement": <float>,
            "coherence_cohesion": <float>,
            "lexical_resource": <float>,
            "grammatical_range": <float>,
            "pronunciation": <float or null>,
            "strengths": ["…"],
            "weaknesses": ["…"],
            "suggestions": ["…"],
            "feedback": "…"
        }}
    ],
    "section_scores": [
        {{"section": "{section}", "band_score": <float>, "detail": "…"}}
    ],
    "overall_band": <float>,
    "strengths": ["…"],
    "weaknesses": ["…"],
    "recommendations": ["…"],
    "final_report_markdown": "# IELTS Practice Report\\n\\n…"
}}"""


# ============================================================================
# Reading Examiner
# ============================================================================

def get_reading_examiner_prompt(
    *,
    difficulty_level: str,
    target_band: str,
    total_questions: int,
    question_number: int,
    exam_variant: str = "academic",
) -> str:
    """System prompt for generating IELTS Reading questions."""
    now = datetime.now(ZoneInfo("UTC"))

    variant_desc = (
        "Academic texts from journals, textbooks, and magazines"
        if exam_variant == "academic"
        else "General Training texts from notices, ads, company handbooks, and newspapers"
    )

    return f"""You are a certified IELTS Reading examiner creating practice questions.

Date: {now.strftime("%Y-%m-%d")}

EXAM CONFIGURATION:
- Variant: {exam_variant.title()}
- Difficulty: {difficulty_level}
- Target band: {target_band}
- Question: #{question_number + 1} of {total_questions}

TEXT TYPE: {variant_desc}

IELTS READING QUESTION TYPES:
• Multiple choice (A-D)
• True / False / Not Given
• Matching headings
• Sentence completion
• Short answer questions
• Summary completion

RULES:
1. Provide a short passage (150-250 words) relevant to the question
2. Ask ONE question about the passage
3. Use a variety of question types across questions
4. Adjust complexity to match the target band
5. For MCQ, provide 4 options (A-D)
6. Include the correct answer in your response
7. Make passages on diverse academic topics

Output a JSON object:
{{
    "passage": "The full reading passage text...",
    "question": "The question text...",
    "question_type": "multiple_choice|true_false_ng|fill_blank|short_answer",
    "options": ["A) ...", "B) ...", "C) ...", "D) ..."],
    "correct_answer": "B"
}}"""


# ============================================================================
# Listening Examiner
# ============================================================================

def get_listening_examiner_prompt(
    *,
    difficulty_level: str,
    target_band: str,
    total_questions: int,
    question_number: int,
) -> str:
    """System prompt for generating IELTS Listening questions."""
    now = datetime.now(ZoneInfo("UTC"))

    part = 1 if question_number < 3 else (2 if question_number < 6 else 3)

    part_descs = {
        1: "A conversation in a social context (e.g., booking, inquiry)",
        2: "A monologue in a social context (e.g., speech, tour guide)",
        3: "A conversation in an academic context (e.g., tutorial discussion)",
    }

    return f"""You are a certified IELTS Listening examiner creating practice questions.

Date: {now.strftime("%Y-%m-%d")}

EXAM CONFIGURATION:
- Difficulty: {difficulty_level}
- Target band: {target_band}
- Question: #{question_number + 1} of {total_questions}
- Section/Part: {part} - {part_descs.get(part, '')}

RULES:
1. Describe a realistic audio scenario in detail (what the listener would hear)
2. The scenario should be 4-8 sentences describing the conversation/monologue
3. Ask ONE question about the scenario
4. Use multiple choice (A-D) or fill-in-the-blank format
5. Include the correct answer
6. Make scenarios on diverse real-world topics

Output a JSON object:
{{
    "scenario": "You will hear a conversation between... [detailed description]",
    "question": "What is...?",
    "question_type": "multiple_choice|fill_blank",
    "options": ["A) ...", "B) ...", "C) ...", "D) ..."],
    "correct_answer": "B"
}}"""


# ============================================================================
# User History Context
# ============================================================================

def get_user_history_context(
    *,
    target_band: float,
    current_band: float,
    section_scores: dict[str, float],
    recent_tests: list[dict[str, Any]],
    weaknesses: list[str],
    strengths: list[str],
) -> str:
    """Build context string from user's test history for adaptive generation."""
    history_text = ""
    if recent_tests:
        for i, t in enumerate(recent_tests[:10], 1):
            history_text += f"  Test {i}: "
            if t.get("section"):
                history_text += f"{t['section'].title()} - "
            history_text += f"Band {t.get('band_score', '?')}\n"
    else:
        history_text = "  No previous tests.\n"

    return f"""
--- USER PERFORMANCE CONTEXT ---
Target Band: {target_band}
Current Estimated Band: {current_band}

Section Scores:
  Listening: {section_scores.get('listening', 'N/A')}
  Reading: {section_scores.get('reading', 'N/A')}
  Writing: {section_scores.get('writing', 'N/A')}
  Speaking: {section_scores.get('speaking', 'N/A')}

Last Test Results:
{history_text}

Weakness Patterns: {', '.join(weaknesses) if weaknesses else 'Not yet identified'}
Strengths: {', '.join(strengths) if strengths else 'Not yet identified'}

ADAPTIVE INSTRUCTIONS:
1. Focus more questions on weak areas
2. Gradually increase difficulty toward the target band {target_band}
3. Avoid repeating similar question patterns from recent tests
4. If user improves consistently, push difficulty higher
5. If user struggles, provide slightly easier questions to build confidence
---"""
