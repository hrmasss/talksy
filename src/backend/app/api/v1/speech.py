"""Speech API endpoints – TTS and STT."""

from uuid import UUID

from app.agents.common.llm import get_user_api_key
from app.core.auth import require_auth
from app.core.logging import logger
from app.services.speech import speech_to_text, text_to_speech
from litestar import Controller, Request, post
from litestar.datastructures import UploadFile
from litestar.enums import RequestEncodingType
from litestar.params import Body
from litestar.response import Response
from litestar.status_codes import HTTP_200_OK
from pydantic import BaseModel, Field


class TTSRequest(BaseModel):
    text: str = Field(min_length=1, max_length=5000)
    voice: str = "Kore"


class STTResponse(BaseModel):
    text: str


class SpeechController(Controller):
    """Text-to-Speech and Speech-to-Text endpoints."""

    path = "/speech"
    tags = ["Speech"]

    @post(
        "/tts",
        summary="Text to Speech",
        description="Convert text to spoken audio (WAV). Requires a Gemini API key (user or server).",
        status_code=HTTP_200_OK,
        guards=[require_auth],
    )
    async def tts(self, request: Request, data: TTSRequest) -> Response:
        """Generate speech audio from text."""
        user_id: UUID = request.state.user_id
        api_key = await get_user_api_key(str(user_id))

        audio_bytes = await text_to_speech(
            data.text,
            voice=data.voice,
            api_key=api_key,
        )

        return Response(
            content=audio_bytes,
            media_type="audio/wav",
            headers={"Content-Disposition": "inline; filename=speech.wav"},
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
        data: UploadFile = Body(media_type=RequestEncodingType.MULTI_PART),
    ) -> STTResponse:
        """Transcribe uploaded audio to text."""
        user_id: UUID = request.state.user_id
        api_key = await get_user_api_key(str(user_id))

        audio_bytes = await data.read()
        content_type = data.content_type or "audio/webm"

        transcript = await speech_to_text(
            audio_bytes,
            mime_type=content_type,
            api_key=api_key,
        )

        return STTResponse(text=transcript)
