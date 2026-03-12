"""Text-to-Speech and Speech-to-Text service using Google Gemini.

TTS: Uses the google-genai SDK to generate spoken audio from text.
STT: Uses Gemini's multimodal capabilities to transcribe audio.
"""

from __future__ import annotations

import asyncio
import contextlib
import io
import tempfile
import wave
from pathlib import Path

from google import genai
from google.genai import errors as genai_errors
from google.genai import types

from app.agents.common.llm import next_api_key
from app.config import settings
from app.core.logging import logger


def _get_client(api_key: str | None = None) -> genai.Client:
    """Create a Google GenAI client with the given or next pooled key."""
    key = api_key or next_api_key()
    return genai.Client(api_key=key)


def _get_audio_cache_dir() -> Path:
    """Get the audio cache directory, creating it if needed."""
    cache_dir = Path(settings.static_dir) / "audio" / "cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir


def _get_cached_audio_path(text_hash: str) -> Path:
    """Return the path for a cached audio file based on text hash."""
    import hashlib
    safe_hash = hashlib.sha256(text_hash.encode()).hexdigest()[:16]
    return _get_audio_cache_dir() / f"{safe_hash}.wav"


async def cache_audio_file(text: str, audio_bytes: bytes) -> str:
    """Cache audio bytes to disk and return the relative URL path.
    
    Returns: URL path like "/static/audio/cache/abc123def456.wav"
    """
    import hashlib
    text_hash = hashlib.sha256(text.encode()).hexdigest()[:16]
    path = _get_cached_audio_path(text_hash)
    
    if not path.exists():
        path.write_bytes(audio_bytes)
        logger.info("Cached audio file: {}", path.relative_to(settings.static_dir))
    
    return f"/static/audio/cache/{text_hash}.wav"


def _pcm_to_wav(audio_bytes: bytes, sample_rate: int) -> bytes:
    """Wrap raw 16-bit mono PCM bytes in a WAV container."""
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(audio_bytes)
    return buffer.getvalue()


def _sample_rate_from_mime_type(mime_type: str | None) -> int:
    """Extract the sample rate from a MIME type when it is available."""
    if not mime_type:
        return settings.gemini_tts_sample_rate

    for part in mime_type.split(";"):
        name, _, value = part.strip().partition("=")
        if name.lower() == "rate":
            try:
                return int(value)
            except ValueError:
                break

    return settings.gemini_tts_sample_rate


def _file_suffix_for_mime_type(mime_type: str) -> str:
    """Choose a temporary filename suffix based on the uploaded MIME type."""
    suffix_map = {
        "audio/webm": ".webm",
        "audio/wav": ".wav",
        "audio/x-wav": ".wav",
        "audio/mpeg": ".mp3",
        "audio/mp3": ".mp3",
        "audio/ogg": ".ogg",
        "audio/ogg; codecs=opus": ".ogg",
        "audio/mp4": ".m4a",
    }
    return suffix_map.get(mime_type.lower(), ".audio")


# ── Text-to-Speech ────────────────────────────────────────────────


async def text_to_speech(
    text: str,
    *,
    voice: str = "Kore",
    api_key: str | None = None,
) -> bytes:
    """Convert *text* to speech audio (WAV) via Gemini's preview TTS model.

    Returns raw WAV bytes.
    """
    client = _get_client(api_key)
    model = settings.gemini_tts_model

    try:
        response = client.models.generate_content(
            model=model,
            contents=text,
            config=types.GenerateContentConfig(
                response_modalities=["AUDIO"],
                speech_config=types.SpeechConfig(
                    voice_config=types.VoiceConfig(
                        prebuilt_voice_config=types.PrebuiltVoiceConfig(
                            voice_name=voice,
                        )
                    )
                ),
            )
        )
    except genai_errors.APIError as exc:
        logger.warning("Gemini TTS request failed: {}", exc)
        raise RuntimeError("Text-to-speech generation failed") from exc

    if not response.candidates:
        raise RuntimeError("Gemini returned no TTS candidates")

    candidate = response.candidates[0]
    if not candidate.content or not candidate.content.parts:
        raise RuntimeError("Gemini returned no audio content")

    for part in candidate.content.parts:
        if not part.inline_data or not part.inline_data.data:
            continue
        mime_type = part.inline_data.mime_type
        audio_bytes = part.inline_data.data
        if mime_type and mime_type.startswith("audio/wav"):
            return audio_bytes
        return _pcm_to_wav(audio_bytes, _sample_rate_from_mime_type(mime_type))

    raise RuntimeError("Gemini returned no audio data")


# ── Speech-to-Text ────────────────────────────────────────────────


async def speech_to_text(
    audio_bytes: bytes,
    mime_type: str = "audio/webm",
    *,
    api_key: str | None = None,
) -> str:
    """Transcribe *audio_bytes* to text via Gemini's uploaded-file workflow.

    Accepts any audio format Gemini supports (webm, mp3, wav, ogg, etc.).
    """
    client = _get_client(api_key)
    model = settings.gemini_stt_model
    temp_path: Path | None = None
    uploaded_audio = None

    try:
        with tempfile.NamedTemporaryFile(
            delete=False,
            suffix=_file_suffix_for_mime_type(mime_type),
        ) as temp_file:
            temp_file.write(audio_bytes)
            temp_path = Path(temp_file.name)

        uploaded_audio = client.files.upload(file=str(temp_path))
        response = client.models.generate_content(
            model=model,
            contents=[
                types.Part.from_uri(
                    file_uri=uploaded_audio.uri,
                    mime_type=uploaded_audio.mime_type,
                ),
                (
                    "Transcribe this audio accurately. "
                    "Provide only the transcription without any additional commentary."
                ),
            ],
        )
    except genai_errors.APIError as exc:
        logger.warning("Gemini STT request failed: {}", exc)
        raise RuntimeError("Speech-to-text transcription failed") from exc
    finally:
        if uploaded_audio is not None:
            with contextlib.suppress(Exception):
                client.files.delete(name=uploaded_audio.name)
        if temp_path is not None:
            with contextlib.suppress(FileNotFoundError):
                temp_path.unlink()

    if response.text:
        return response.text.strip()

    if response.candidates:
        candidate = response.candidates[0]
        if candidate.content and candidate.content.parts:
            for part in candidate.content.parts:
                if part.text:
                    return part.text.strip()

    raise RuntimeError("Gemini returned no transcription text")


# ── Optimized Text + Audio Generation (Single Call or Parallel) ─────────────


async def generate_text_and_audio(
    prompt: str,
    *,
    voice: str = "Kore",
    api_key: str | None = None,
    parallel_mode: bool = True,
) -> tuple[str, bytes]:
    """Generate both text and audio in a single API call or parallel calls.
    
    This is optimized to avoid sequential API calls. Returns (text, audio_bytes).
    
    If Gemini supports TEXT + AUDIO in one call, uses that.
    Otherwise generates text and audio in parallel for speed.
    """
    if parallel_mode:
        # Parallel mode: generate text (TEXT modality) and audio (AUDIO modality) in parallel
        return await _generate_text_and_audio_parallel(prompt, voice=voice, api_key=api_key)
    else:
        # Single call: request both modalities at once (if API supports it)
        return await _generate_text_and_audio_combined(prompt, voice=voice, api_key=api_key)


async def _generate_text_and_audio_parallel(
    prompt: str,
    *,
    voice: str = "Kore",
    api_key: str | None = None,
) -> tuple[str, bytes]:
    """Generate text and audio in parallel (faster than sequential).
    
    Launches two async tasks simultaneously to get both results faster.
    """
    client = _get_client(api_key)
    model = settings.gemini_tts_model  # Use TTS model which supports both
    
    async def _get_text() -> str:
        """Generate text response only (TEXT modality)."""
        try:
            response = client.models.generate_content(
                model=model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_modalities=["TEXT"],
                )
            )
            if response.text:
                return response.text.strip()
            if response.candidates:
                candidate = response.candidates[0]
                if candidate.content and candidate.content.parts:
                    for part in candidate.content.parts:
                        if part.text:
                            return part.text.strip()
            return ""
        except genai_errors.APIError as exc:
            logger.warning("Gemini text generation failed: {}", exc)
            raise RuntimeError("Text generation failed") from exc
    
    async def _get_audio() -> bytes:
        """Generate audio response only (AUDIO modality)."""
        try:
            response = client.models.generate_content(
                model=model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_modalities=["AUDIO"],
                    speech_config=types.SpeechConfig(
                        voice_config=types.VoiceConfig(
                            prebuilt_voice_config=types.PrebuiltVoiceConfig(
                                voice_name=voice,
                            )
                        )
                    ),
                )
            )
            if not response.candidates:
                raise RuntimeError("Gemini returned no audio candidates")
            
            candidate = response.candidates[0]
            if not candidate.content or not candidate.content.parts:
                raise RuntimeError("Gemini returned no audio content")

            for part in candidate.content.parts:
                if not part.inline_data or not part.inline_data.data:
                    continue
                mime_type = part.inline_data.mime_type
                audio_bytes = part.inline_data.data
                if mime_type and mime_type.startswith("audio/wav"):
                    return audio_bytes
                return _pcm_to_wav(audio_bytes, _sample_rate_from_mime_type(mime_type))
            
            raise RuntimeError("Gemini returned no audio data")
        except genai_errors.APIError as exc:
            logger.warning("Gemini audio generation failed: {}", exc)
            raise RuntimeError("Audio generation failed") from exc
    
    # Run both requests in parallel for faster completion
    try:
        text, audio_bytes = await asyncio.gather(_get_text(), _get_audio())
        return text, audio_bytes
    except RuntimeError as exc:
        logger.error("Text and audio generation failed: {}", exc)
        raise


async def _generate_text_and_audio_combined(
    prompt: str,
    *,
    voice: str = "Kore",
    api_key: str | None = None,
) -> tuple[str, bytes]:
    """Generate text and audio in a single API call (if supported).
    
    Falls back to parallel mode if combined mode doesn't work.
    """
    client = _get_client(api_key)
    model = settings.gemini_tts_model
    
    try:
        # Request both TEXT and AUDIO modalities in one call
        response = client.models.generate_content(
            model=model,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_modalities=["TEXT", "AUDIO"],
                speech_config=types.SpeechConfig(
                    voice_config=types.VoiceConfig(
                        prebuilt_voice_config=types.PrebuiltVoiceConfig(
                            voice_name=voice,
                        )
                    )
                ),
            )
        )
        
        text = ""
        audio_bytes = b""
        
        if response.candidates:
            candidate = response.candidates[0]
            if candidate.content and candidate.content.parts:
                for part in candidate.content.parts:
                    # Extract text
                    if part.text:
                        text = part.text.strip()
                    # Extract audio
                    elif part.inline_data and part.inline_data.data:
                        mime_type = part.inline_data.mime_type
                        raw_audio = part.inline_data.data
                        if mime_type and mime_type.startswith("audio/wav"):
                            audio_bytes = raw_audio
                        else:
                            audio_bytes = _pcm_to_wav(
                                raw_audio,
                                _sample_rate_from_mime_type(mime_type),
                            )
        
        if not text or not audio_bytes:
            logger.warning("Combined mode didn't return both, falling back to parallel")
            return await _generate_text_and_audio_parallel(prompt, voice=voice, api_key=api_key)
        
        return text, audio_bytes
        
    except genai_errors.APIError as exc:
        logger.warning("Combined text+audio generation failed, falling back to parallel: {}", exc)
        return await _generate_text_and_audio_parallel(prompt, voice=voice, api_key=api_key)

