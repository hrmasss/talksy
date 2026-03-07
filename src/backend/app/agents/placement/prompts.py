"""Prompts for the IELTS placement test agent."""

from __future__ import annotations


def get_placement_listening_prompt(question_num: int, total: int) -> str:
    """Generate a listening comprehension question for placement."""
    return f"""You are an IELTS examiner conducting a quick diagnostic placement test.

TASK: Generate a LISTENING comprehension question ({question_num}/{total} for this section).

Requirements:
- Create a short real-world audio scenario description (e.g. "You will hear a conversation between a student and a librarian about...")
- Then provide 1 question about the scenario
- For Q1-2: multiple choice (4 options, label A-D)
- For Q3: fill-in-the-blank

The scenario should be 3-5 sentences describing what the listener would hear.
Keep difficulty moderate (band 5-6 level) to gauge baseline ability.

Respond with ONLY a JSON object:
{{
    "scenario": "You will hear... [describe the audio scenario in detail]",
    "question": "What is...?",
    "question_type": "multiple_choice" or "fill_blank",
    "options": ["A) ...", "B) ...", "C) ...", "D) ..."] or [],
    "correct_answer": "B" or "the exact fill-in answer"
}}"""


def get_placement_reading_prompt(question_num: int, total: int) -> str:
    """Generate a reading comprehension question for placement."""
    return f"""You are an IELTS examiner conducting a quick diagnostic placement test.

TASK: Generate a READING comprehension question ({question_num}/{total} for this section).

Requirements:
- Provide a short academic-style passage (80-120 words)
- Ask 1 comprehension question about it
- Use multiple choice format (4 options, label A-D)
- Keep difficulty moderate (band 5-6 level) to gauge baseline ability
- Use diverse topics across questions (science, history, culture, etc.)

Respond with ONLY a JSON object:
{{
    "passage": "...",
    "question": "According to the passage, ...?",
    "question_type": "multiple_choice",
    "options": ["A) ...", "B) ...", "C) ...", "D) ..."],
    "correct_answer": "C"
}}"""


def get_placement_writing_prompt() -> str:
    """Generate a writing prompt for placement."""
    return """You are an IELTS examiner conducting a quick diagnostic placement test.

TASK: Generate a SHORT IELTS-style Writing prompt.

Requirements:
- A clear, debatable topic suitable for a 100-150 word response
- Similar to IELTS Writing Task 2 but shorter
- Should test: grammar, vocabulary, coherence, task achievement
- Moderate difficulty

Respond with ONLY a JSON object:
{
    "prompt": "Some people believe that... To what extent do you agree or disagree? Write 100-150 words.",
    "question_type": "essay",
    "min_words": 100,
    "max_words": 150
}"""


def get_placement_speaking_prompt(question_num: int, total: int) -> str:
    """Generate a speaking question for placement."""
    if question_num == 1:
        style = "Part 1 style - a simple personal question about daily life, hobbies, or hometown"
    else:
        style = "Part 2 style - describe something (a place, experience, or person) in 3-5 sentences"

    return f"""You are an IELTS examiner conducting a quick diagnostic placement test.

TASK: Generate a SPEAKING question ({question_num}/{total} for this section).

Requirements:
- {style}
- The user will type their response (simulating spoken English)
- Keep it simple enough to answer in 2-5 sentences

Respond with ONLY a JSON object:
{{
    "question": "...",
    "question_type": "speaking",
    "instructions": "Please type your spoken response (2-5 sentences)."
}}"""


def get_placement_evaluation_prompt(responses: list[dict]) -> str:
    """Evaluate all placement test responses and produce a skill profile."""
    responses_text = ""
    for i, r in enumerate(responses, 1):
        responses_text += f"\n--- Response {i} ({r['section'].upper()}) ---\n"
        responses_text += f"Question: {r['question']}\n"
        if r.get('passage'):
            responses_text += f"Passage: {r['passage'][:200]}...\n"
        responses_text += f"Answer: {r['answer']}\n"
        if r.get('correct_answer'):
            responses_text += f"Correct: {r['correct_answer']}\n"

    return f"""You are a senior IELTS examiner evaluating a diagnostic placement test.

The candidate completed a short placement test across all four IELTS sections.
Evaluate their responses and estimate their current IELTS band score.

CANDIDATE RESPONSES:
{responses_text}

EVALUATION TASK:
1. Score each section (Listening, Reading, Writing, Speaking) on the IELTS 0-9 band scale
2. Calculate overall estimated band (average, rounded to nearest 0.5)
3. Identify strengths and weaknesses
4. Recommend focus areas for improvement

ASSESSMENT CRITERIA:
- Listening & Reading: accuracy of answers
- Writing: task achievement, coherence, vocabulary range, grammar accuracy
- Speaking: fluency simulation, vocabulary, grammar, idea development

Respond with ONLY a JSON object:
{{
    "listening_band": <float>,
    "reading_band": <float>,
    "writing_band": <float>,
    "speaking_band": <float>,
    "overall_band": <float>,
    "strengths": ["...", "..."],
    "weaknesses": ["...", "..."],
    "focus_areas": ["...", "..."],
    "section_analysis": {{
        "listening": "Brief analysis...",
        "reading": "Brief analysis...",
        "writing": "Brief analysis...",
        "speaking": "Brief analysis..."
    }},
    "feedback_markdown": "# Placement Test Results\\n\\n## Overall Band: X.X\\n\\n..."
}}"""
