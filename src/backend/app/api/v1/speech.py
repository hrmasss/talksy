"""Speech API endpoints - TTS and STT."""

from typing import ClassVar
from uuid import UUID

from litestar import Controller, Request, post
from litestar.datastructures import UploadFile
from litestar.enums import RequestEncodingType
from litestar.params import Body
from litestar.response import Response
from litestar.response import Stream
from litestar.status_codes import HTTP_200_OK
from pydantic import BaseModel, Field
from app.agents.common.llm import get_user_api_key
from app.core.auth import require_auth
from app.config import settings
from app.core.exceptions import AIServiceException
from app.core.logging import logger
from app.services.speech import speech_to_text, stream_text_to_speech, text_to_speech


MULTIPART_BODY = Body(media_type=RequestEncodingType.MULTI_PART)


class TTSRequest(BaseModel):
    text: str = Field(min_length=1, max_length=5000)
    voice: str = "troy"


class STTResponse(BaseModel):
    text: str


class SpeechController(Controller):
    """Text-to-Speech and Speech-to-Text endpoints."""

    path = "/speech"
    tags: ClassVar[list[str]] = ["Speech"]

    @post(
        "/tts",
        summary="Text to Speech",
        description=(
            "Convert text to spoken audio (WAV). "
            "Requires a Groq API key (user or server)."
        ),
        status_code=HTTP_200_OK,
        guards=[require_auth],
    )
    async def tts(self, request: Request, data: TTSRequest) -> Response:
        """Generate speech audio from text."""
        user_id: UUID = request.state.user_id
        api_key = await get_user_api_key(str(user_id))

        try:
            audio_bytes = await text_to_speech(
                data.text,
                voice=data.voice,
                api_key=api_key,
            )
        except RuntimeError as exc:
            logger.warning("TTS failed for user {}: {}", user_id, exc)
            raise AIServiceException(detail=str(exc)) from exc

        return Response(
            content=audio_bytes,
            media_type="audio/wav",
            headers={"Content-Disposition": "inline; filename=speech.wav"},
        )

    @post(
        "/tts/stream",
        summary="Stream Text to Speech",
        description=(
            "Convert text to spoken audio and stream PCM chunks as they are generated. "
            "Requires a Groq API key (user or server)."
        ),
        status_code=HTTP_200_OK,
        guards=[require_auth],
    )
    async def tts_stream(self, request: Request, data: TTSRequest) -> Stream:
        """Stream speech audio from text."""
        user_id: UUID = request.state.user_id
        api_key = await get_user_api_key(str(user_id))

        async def iterator():
            try:
                async for chunk in stream_text_to_speech(
                    data.text,
                    voice=data.voice,
                    api_key=api_key,
                ):
                    yield chunk
            except RuntimeError as exc:
                logger.warning("Streaming TTS failed for user {}: {}", user_id, exc)
                raise AIServiceException(detail=str(exc)) from exc

        return Stream(
            content=iterator,
            media_type="audio/pcm",
            headers={
                "X-Audio-Sample-Rate": str(settings.groq_tts_sample_rate),
                "X-Audio-Channels": "1",
                "X-Audio-Bits-Per-Sample": "16",
                "Content-Disposition": "inline; filename=speech.pcm",
            },
        )

    @post(
        "/stt",
        summary="Speech to Text",
        description="Transcribe audio to text. Upload audio as multipart form data.",
        status_code=HTTP_200_OK,
        guards=[require_auth],
    )
    async def stt(
        self,
        request: Request,
        data: UploadFile = MULTIPART_BODY,
    ) -> STTResponse:
        """Transcribe uploaded audio to text."""
        user_id: UUID = request.state.user_id
        api_key = await get_user_api_key(str(user_id))

        audio_bytes = await data.read()
        content_type = data.content_type or "audio/webm"

        try:
            transcript = await speech_to_text(
                audio_bytes,
                mime_type=content_type,
                api_key=api_key,
            )
        except RuntimeError as exc:
            logger.warning("STT failed for user {}: {}", user_id, exc)
            raise AIServiceException(detail=str(exc)) from exc

        return STTResponse(text=transcript)
