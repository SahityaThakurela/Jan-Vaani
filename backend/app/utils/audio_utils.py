"""
Jan Vaani — Audio Utilities
Helpers for audio format conversion and base64 encoding/decoding.
"""
import base64
import io
from typing import Optional
from app.utils.logger import get_logger

logger = get_logger(__name__)


def audio_bytes_to_base64(audio_bytes: bytes) -> str:
    """Convert raw audio bytes to a base64 string for JSON transport."""
    return base64.b64encode(audio_bytes).decode("utf-8")


def base64_to_audio_bytes(b64_string: str) -> bytes:
    """Convert a base64 string back to raw audio bytes."""
    return base64.b64decode(b64_string)


def get_audio_duration_seconds(audio_bytes: bytes, sample_rate: int = 22050, channels: int = 1, sample_width: int = 2) -> float:
    """
    Estimate PCM audio duration in seconds.
    For MP3, returns a rough estimate based on bytes.
    """
    try:
        # Rough estimate: MP3 at 128kbps → 16000 bytes/sec
        # This is approximate; use pydub for precise duration if needed
        bytes_per_second = 16000
        return len(audio_bytes) / bytes_per_second
    except Exception as e:
        logger.warning(f"Could not estimate audio duration: {e}")
        return 0.0


def validate_audio_bytes(audio_bytes: bytes) -> bool:
    """Basic validation that audio_bytes is non-empty."""
    return audio_bytes is not None and len(audio_bytes) > 0
