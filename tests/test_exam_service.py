from __future__ import annotations

import pytest

from app.agents.services.exam_service import ExamService


@pytest.mark.asyncio
async def test_format_question_response_uses_current_question_fields() -> None:
    result = await ExamService._format_question_response(
        {
            "status": "in_progress",
            "exam_section": "speaking",
            "current_part": 2,
            "question_number": 3,
            "total_questions": 10,
            "current_question": "Describe a memorable journey.",
            "current_question_type": "cue_card",
        },
        thread_id="thread-1",
    )

    assert result["section"] == "speaking"
    assert result["question_index"] == 3
    assert result["current_question"] == {
        "text": "Describe a memorable journey.",
        "type": "cue_card",
    }


@pytest.mark.asyncio
async def test_format_question_response_falls_back_to_latest_question_history() -> None:
    result = await ExamService._format_question_response(
        {
            "status": "in_progress",
            "section": "reading",
            "question_number": 1,
            "total_questions": 8,
            "questions_asked": [
                {"text": "Read the passage and answer the question.", "type": "multiple_choice"}
            ],
        },
        thread_id="thread-2",
    )

    assert result["section"] == "reading"
    assert result["current_question"] == {
        "text": "Read the passage and answer the question.",
        "type": "multiple_choice",
    }