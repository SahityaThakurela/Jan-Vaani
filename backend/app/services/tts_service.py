"""
Jan Vaani — TTS Service (Rime)

Converts agent text → spoken audio bytes via Rime's TTS API.

MODEL STRATEGY:
- English: Rime "mist" model with Indian-English speaker "maya" (low-latency)
- Hindi:   Rime "coda" model with speaker "nadi" or "taru" + lang="hin"
           The "mist" model does NOT support Hindi; "coda" is required.

IMPORTANT Rime Coda notes:
- No SSML/emotion tags supported. Delivery is shaped via wording and punctuation only.
- Short sentences with commas/periods produce more natural pacing.
- For Coda requests the "lang" field is mandatory when using non-English voices.
"""
import httpx
from app.config import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)

# Hindi voices available on Rime Coda: "nadi" (female), "taru" (female)
HINDI_SPEAKER = "nadi"
HINDI_MODEL = "coda"
HINDI_LANG = "hin"


async def synthesize_speech(
    text: str,
    language: str = "hi",
    speed_alpha: float = 0.9,
) -> bytes:
    """
    Convert text to speech via Rime TTS.

    - Hindi  → Coda model, speaker="nadi", lang="hin"
    - English → Mist model, speaker=settings.rime_speaker (default: maya)

    Args:
        text: The agent reply text (max ~500 chars for natural delivery)
        language: "hi" or "en"
        speed_alpha: Speed multiplier (0.9 = slightly slower = clearer for rural users)

    Returns:
        Raw audio bytes (MP3 format)
    """
    if not settings.rime_api_key:
        logger.warning("No Rime API key — returning empty audio bytes.")
        return b""

    # Ensure text ends with punctuation for natural cadence
    text = text.strip()
    if text and text[-1] not in ".!?।":
        # Use Hindi full-stop for Hindi text, period otherwise
        text += "।" if language == "hi" else "."

    # ── Select model + speaker based on language ──────────────
    if language == "hi":
        model_id = HINDI_MODEL
        speaker = HINDI_SPEAKER
    else:
        model_id = settings.rime_model   # "mist"
        speaker = settings.rime_speaker  # "maya"

    payload = {
        "speaker": speaker,
        "text": text,
        "modelId": model_id,
        "audioFormat": settings.rime_audio_format,
        "samplingRate": settings.rime_sampling_rate,
        "speedAlpha": speed_alpha,
        "reduceLatency": True,
    }

    # Coda model requires "lang" field for non-English voices
    if language == "hi":
        payload["lang"] = HINDI_LANG

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
                f"Rime TTS [{language}]: {len(text)} chars → {len(audio_bytes)} bytes "
                f"[model={model_id}, speaker={speaker}]"
            )
            return audio_bytes

    except httpx.HTTPStatusError as e:
        logger.error(
            f"Rime TTS HTTP error {e.response.status_code}: {e.response.text[:300]}"
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
