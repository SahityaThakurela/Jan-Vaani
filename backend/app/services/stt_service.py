"""
Jan Vaani — STT Service (Deepgram Nova-2)
Converts audio bytes → transcript text.
"""
import httpx
from app.config import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)

DEEPGRAM_URL = "https://api.deepgram.com/v1/listen"


async def transcribe_audio(
    audio_bytes: bytes,
    language: str = "hi",
    mimetype: str = "audio/webm",
) -> dict:
    """
    Send audio to Deepgram Nova-2 and return transcript.

    Args:
        audio_bytes: Raw audio bytes (webm, wav, mp3, etc.)
        language: "hi" or "en"
        mimetype: MIME type of the audio

    Returns:
        {"transcript": str, "confidence": float, "words": [...]}
    """
    if not settings.deepgram_api_key:
        logger.warning("No Deepgram API key — returning stub transcript.")
        return {"transcript": "[STT unavailable — no API key]", "confidence": 0.0, "words": []}

    # Map language code to Deepgram language code
    lang_map = {"hi": "hi", "en": "en-IN"}
    dg_language = lang_map.get(language, "hi")

    params = {
        "model": settings.deepgram_model,
        "language": dg_language,
        "punctuate": "true",
        "smart_format": "true",
        "filler_words": "false",
        "utterances": "false",
    }

    headers = {
        "Authorization": f"Token {settings.deepgram_api_key}",
    }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                DEEPGRAM_URL,
                content=audio_bytes,
                headers=headers,
                params=params,
            )
            response.raise_for_status()
            data = response.json()

        channel = data["results"]["channels"][0]["alternatives"][0]
        transcript = channel.get("transcript", "").strip()
        confidence = channel.get("confidence", 0.0)
        words = channel.get("words", [])

        logger.info(f"Transcript [{language}] (conf={confidence:.2f}): {transcript[:80]}")
        return {
            "transcript": transcript,
            "confidence": confidence,
            "words": words,
        }

    except httpx.HTTPStatusError as e:
        logger.error(f"Deepgram HTTP error {e.response.status_code}: {e.response.text}")
        return {"transcript": "", "confidence": 0.0, "words": []}
    except Exception as e:
        logger.error(f"Deepgram transcription failed: {e}")
        return {"transcript": "", "confidence": 0.0, "words": []}
