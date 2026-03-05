"""Conversation API endpoints."""

from uuid import UUID

from litestar import Controller, get, post
from litestar.status_codes import HTTP_200_OK, HTTP_201_CREATED

from app.schemas.conversation import (
    ConversationStart,
    ConversationMessage,
    ConversationResponse,
    ConversationSessionResponse,
    ConversationMessageResponse,
)
from app.services.conversation import conversation_service


class ConversationController(Controller):
    """Conversation practice controller."""

    path = "/conversations"
    tags = ["Conversations"]

    @post(
        "/",
        summary="Start Conversation",
        description="Start a new conversation practice session.",
        status_code=HTTP_201_CREATED,
    )
    async def start_conversation(
        self, data: ConversationStart
    ) -> ConversationSessionResponse:
        """Start a new conversation session."""
        # TODO: Get user_id from authentication
        from uuid import uuid4
        user_id = uuid4()  # Placeholder

        session = await conversation_service.start_session(user_id, data)
        return ConversationSessionResponse(
            id=session.id,
            user_id=user_id,
            topic=session.topic,
            scenario=session.scenario,
            difficulty_level=session.difficulty_level,
            started_at=session.started_at,
            ended_at=None,
            duration_seconds=0,
            message_count=1,
            vocabulary_used=[],
            grammar_score=None,
            fluency_score=None,
            coherence_score=None,
            overall_score=None,
            ai_summary=None,
            ai_suggestions=[],
        )

    @post(
        "/{session_id:uuid}/messages",
        summary="Send Message",
        description="Send a message in the conversation.",
        status_code=HTTP_201_CREATED,
    )
    async def send_message(
        self, session_id: UUID, data: ConversationMessage
    ) -> ConversationResponse:
        """Send a message and get AI response."""
        # TODO: Get user_id from authentication
        from uuid import uuid4
        from datetime import datetime, timezone
        user_id = uuid4()  # Placeholder

        result = await conversation_service.send_message(session_id, user_id, data)
        
        return ConversationResponse(
            message=ConversationMessageResponse(
                id=result["ai_message"]["id"],
                role="assistant",
                content=result["ai_message"]["content"],
                audio_url=None,
                timestamp=datetime.now(timezone.utc),
                analysis={},
            ),
            suggestions=result.get("suggestions", []),
            vocabulary_tips=result.get("vocabulary_tips", []),
            grammar_notes=result.get("grammar_notes", []),
        )

    @post(
        "/{session_id:uuid}/end",
        summary="End Conversation",
        description="End the conversation session and get analysis.",
        status_code=HTTP_200_OK,
    )
    async def end_conversation(
        self, session_id: UUID
    ) -> ConversationSessionResponse:
        """End conversation and get summary."""
        # TODO: Get user_id from authentication
        from uuid import uuid4
        user_id = uuid4()  # Placeholder

        session = await conversation_service.end_session(session_id, user_id)
        return ConversationSessionResponse(
            id=session["id"],
            user_id=session["user"],
            topic=session["topic"],
            scenario=session.get("scenario"),
            difficulty_level=session["difficulty_level"],
            started_at=session["started_at"],
            ended_at=session.get("ended_at"),
            duration_seconds=session["duration_seconds"],
            message_count=session["message_count"],
            vocabulary_used=session.get("vocabulary_used", []),
            grammar_score=session.get("grammar_score"),
            fluency_score=session.get("fluency_score"),
            coherence_score=session.get("coherence_score"),
            overall_score=session.get("overall_score"),
            ai_summary=session.get("ai_summary"),
            ai_suggestions=session.get("ai_suggestions", []),
        )

    @get(
        "/{session_id:uuid}",
        summary="Get Conversation",
        description="Get conversation session details.",
        status_code=HTTP_200_OK,
    )
    async def get_conversation(
        self, session_id: UUID
    ) -> ConversationSessionResponse:
        """Get conversation session."""
        session = await conversation_service.get_by_id(session_id)
        if not session:
            from litestar.exceptions import NotFoundException
            raise NotFoundException(detail="Session not found")

        return ConversationSessionResponse(
            id=session["id"],
            user_id=session["user"],
            topic=session["topic"],
            scenario=session.get("scenario"),
            difficulty_level=session["difficulty_level"],
            started_at=session["started_at"],
            ended_at=session.get("ended_at"),
            duration_seconds=session["duration_seconds"],
            message_count=session["message_count"],
            vocabulary_used=session.get("vocabulary_used", []),
            grammar_score=session.get("grammar_score"),
            fluency_score=session.get("fluency_score"),
            coherence_score=session.get("coherence_score"),
            overall_score=session.get("overall_score"),
            ai_summary=session.get("ai_summary"),
            ai_suggestions=session.get("ai_suggestions", []),
        )

    @get(
        "/",
        summary="List Conversations",
        description="Get list of conversation sessions.",
        status_code=HTTP_200_OK,
    )
    async def list_conversations(
        self,
        page: int = 1,
        page_size: int = 20,
    ) -> list[ConversationSessionResponse]:
        """List conversation sessions."""
        # TODO: Get user_id from authentication
        from uuid import uuid4
        user_id = uuid4()  # Placeholder

        offset = (page - 1) * page_size
        sessions = await conversation_service.get_user_sessions(
            user_id, offset=offset, limit=page_size
        )

        return [
            ConversationSessionResponse(
                id=s["id"],
                user_id=s["user"],
                topic=s["topic"],
                scenario=s.get("scenario"),
                difficulty_level=s["difficulty_level"],
                started_at=s["started_at"],
                ended_at=s.get("ended_at"),
                duration_seconds=s["duration_seconds"],
                message_count=s["message_count"],
                vocabulary_used=s.get("vocabulary_used", []),
                grammar_score=s.get("grammar_score"),
                fluency_score=s.get("fluency_score"),
                coherence_score=s.get("coherence_score"),
                overall_score=s.get("overall_score"),
                ai_summary=s.get("ai_summary"),
                ai_suggestions=s.get("ai_suggestions", []),
            )
            for s in sessions
        ]
