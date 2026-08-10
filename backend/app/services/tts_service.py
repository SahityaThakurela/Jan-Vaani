"""
Jan Vaani — TTS Service (Rime Coda model)

Converts agent text → spoken audio bytes via Rime's Coda model.

IMPORTANT Rime Coda notes:
- No SSML/emotion tags supported. Delivery is shaped via wording and punctuation only.
- Short sentences with commas/periods produce more natural pacing.
- We use the "mist" model (Rime's latest — marketed as "Coda" in hackathon context).
- Speaker voices: "maya" for Indian English, "aria" for standard English.
"""
import httpx
from app.config import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)

# Use speaker defined in settings (e.g. maya for mist model)


async def synthesize_speech(
    text: str,
    language: str = "hi",
    speed_alpha: float = 0.9,
) -> bytes:
    """
    Convert text to speech via Rime Coda model.

    Args:
        text: The agent reply text (max ~500 chars for natural delivery)
        language: "hi" or "en" (determines voice)
        speed_alpha: Speed multiplier (0.8 = slightly slower = clearer for rural users)

    Returns:
        Raw audio bytes (MP3 format)
    """
    if not settings.rime_api_key:
        logger.warning("No Rime API key — returning empty audio bytes.")
        return b""

    speaker = settings.rime_speaker

    # Rime Coda: shape delivery through short sentences + punctuation
    # Ensure text ends with punctuation for natural cadence
    text = text.strip()
    if text and text[-1] not in ".!?":
        text += "."

    payload = {
        "speaker": speaker,
        "text": text,
        "modelId": settings.rime_model,  # "mist" = Coda model
        "audioFormat": settings.rime_audio_format,
        "samplingRate": settings.rime_sampling_rate,
        "speedAlpha": speed_alpha,
        "reduceLatency": True,
    }

    headers = {
        "Authorization": f"Bearer {settings.rime_api_key}",
        "Content-Type": "application/json",
        "Accept": f"audio/{settings.rime_audio_format}",
    }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                settings.rime_api_url,
                json=payload,
                headers=headers,
            )
            response.raise_for_status()
            audio_bytes = response.content
            logger.info(
                f"Rime TTS: {len(text)} chars → {len(audio_bytes)} bytes "
                f"[model={settings.rime_model}, speaker={speaker}]"
            )
            return audio_bytes

    except httpx.HTTPStatusError as e:
        logger.error(
            f"Rime TTS HTTP error {e.response.status_code}: {e.response.text[:200]}"
        )
        return b""
    except Exception as e:
        logger.error(f"Rime TTS failed: {e}")
        return b""


async def synthesize_welcome(language: str = "hi") -> bytes:
    """Pre-baked welcome message audio."""
    text = {
        "hi": "Namaste! Main Jan Vaani hun. Aap kisi sarkari yojana ke baare mein jaanna chahte hain, ya eligibility check karna chahte hain?",
        "en": "Hello! I am Jan Vaani. Would you like to search for a government scheme, or check your eligibility?",
    }.get(language, "Namaste! Main Jan Vaani hun.")
    return await synthesize_speech(text, language)
