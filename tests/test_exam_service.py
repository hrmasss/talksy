from __future__ import annotations

from datetime import datetime

import pytest

from app.agents.services.exam_service import ExamService
from app.db.tables import MockExamSession


class _FakeSelectQuery:
    def __init__(self, columns, rows):
        self.columns = columns
        self.rows = rows
        self.output_kwargs: dict[str, object] | None = None

    def where(self, *_args, **_kwargs):
        return self

    def order_by(self, *_args, **_kwargs):
        return self

    def limit(self, *_args, **_kwargs):
        return self

    def offset(self, *_args, **_kwargs):
        return self

    async def output(self, **kwargs):
        self.output_kwargs = kwargs
        return self.rows


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


@pytest.mark.asyncio
async def test_get_active_session_selects_serialized_columns(monkeypatch: pytest.MonkeyPatch) -> None:
    started_at = datetime(2026, 3, 11, 22, 57, 55)
    captured_queries: list[_FakeSelectQuery] = []

    def fake_select(*columns):
        query = _FakeSelectQuery(
            columns,
            [
                {
                    "thread_id": "thread-1",
                    "section": "speaking",
                    "difficulty": "intermediate",
                    "question_index": 2,
                    "total_questions": 10,
                    "started_at": started_at,
                }
            ],
        )
        captured_queries.append(query)
        return query

    monkeypatch.setattr(MockExamSession, "select", staticmethod(fake_select))

    result = await ExamService.get_active_session("user-1")

    assert result == {
        "thread_id": "thread-1",
        "section": "speaking",
        "difficulty": "intermediate",
        "question_index": 2,
        "total_questions": 10,
        "started_at": started_at.isoformat(),
    }
    assert captured_queries[0].output_kwargs == {}
    assert [column._meta.name for column in captured_queries[0].columns] == [
        "thread_id",
        "section",
        "difficulty",
        "question_index",
        "total_questions",
        "started_at",
    ]


@pytest.mark.asyncio
async def test_list_sessions_selects_serialized_columns(monkeypatch: pytest.MonkeyPatch) -> None:
    started_at = datetime(2026, 3, 11, 22, 57, 55)
    completed_at = datetime(2026, 3, 11, 23, 5, 0)
    captured_queries: list[_FakeSelectQuery] = []

    def fake_select(*columns):
        query = _FakeSelectQuery(
            columns,
            [
                {
                    "thread_id": "thread-2",
                    "section": "reading",
                    "difficulty": "advanced",
                    "status": "completed",
                    "question_index": 8,
                    "total_questions": 8,
                    "band_score": 7.5,
                    "section_scores": [7.5],
                    "strengths": ["timing"],
                    "weaknesses": ["detail"],
                    "recommendations": ["practice skimming"],
                    "report_markdown": "report",
                    "started_at": started_at,
                    "completed_at": completed_at,
                }
            ],
        )
        captured_queries.append(query)
        return query

    monkeypatch.setattr(MockExamSession, "select", staticmethod(fake_select))

    result = await ExamService.list_sessions("user-1", status="completed", limit=10, offset=0)

    assert result == [
        {
            "thread_id": "thread-2",
            "section": "reading",
            "difficulty": "advanced",
            "status": "completed",
            "question_index": 8,
            "total_questions": 8,
            "band_score": 7.5,
            "section_scores": [7.5],
            "strengths": ["timing"],
            "weaknesses": ["detail"],
            "recommendations": ["practice skimming"],
            "report_markdown": "report",
            "started_at": started_at.isoformat(),
            "completed_at": completed_at.isoformat(),
        }
    ]
    assert captured_queries[0].output_kwargs == {}
    assert [column._meta.name for column in captured_queries[0].columns] == [
        "thread_id",
        "section",
        "difficulty",
        "status",
        "question_index",
        "total_questions",
        "band_score",
        "section_scores",
        "strengths",
        "weaknesses",
        "recommendations",
        "report_markdown",
        "started_at",
        "completed_at",
    ]