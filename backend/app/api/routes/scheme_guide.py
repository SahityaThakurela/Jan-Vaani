"""
Jan Vaani - Scheme How-To-Apply Route
POST /schemes/how-to-apply
"""
import base64
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional

from app.services import tts_service, llm_service
from app.utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter()


class HowToApplyRequest(BaseModel):
    scheme_name_en: str
    scheme_name_hi: Optional[str] = None
    language: str = "hi"


class ApplyStep(BaseModel):
    step_number: int
    title: str
    description: str


class HowToApplyResponse(BaseModel):
    scheme_name: str
    steps: List[ApplyStep]
    documents: List[str]
    summary_text: str
    audio_b64: Optional[str] = None


@router.post("/how-to-apply", response_model=HowToApplyResponse)
async def how_to_apply(req: HowToApplyRequest):
    """Generate step-by-step guide + documents + TTS audio for a scheme."""
    scheme_display = req.scheme_name_en
    if req.scheme_name_hi:
        scheme_display = f"{req.scheme_name_en} ({req.scheme_name_hi})"

    try:
        guide_data = await llm_service.generate_how_to_apply(
            scheme_name_en=req.scheme_name_en,
            scheme_name_hi=req.scheme_name_hi,
            language=req.language,
        )
    except Exception as e:
        logger.error(f"How-to-apply LLM call failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate application guide.")

    steps = guide_data.get("steps", [])
    documents = guide_data.get("documents", [])

    if req.language == "hi":
        spoken_parts = [f"{req.scheme_name_en} mein aavedan karne ke liye:"]
        for s in steps:
            spoken_parts.append(f"Charan {s['step_number']}: {s['title']}. {s['description']}")
        if documents:
            spoken_parts.append("Aavashyak dastavez: " + ", ".join(documents[:4]) + ".")
    else:
        spoken_parts = [f"How to apply for {scheme_display}:"]
        for s in steps:
            spoken_parts.append(f"Step {s['step_number']}: {s['title']}. {s['description']}")
        if documents:
            spoken_parts.append("Required documents: " + ", ".join(documents[:4]) + ".")

    summary_text = " ".join(spoken_parts)
    tts_text = summary_text[:800]

    try:
        audio_bytes = await tts_service.synthesize_speech(tts_text, req.language)
        audio_b64 = base64.b64encode(audio_bytes).decode("utf-8") if audio_bytes else None
    except Exception as e:
        logger.error(f"TTS for how-to-apply failed: {e}")
        audio_b64 = None

    return HowToApplyResponse(
        scheme_name=scheme_display,
        steps=[ApplyStep(**s) for s in steps],
        documents=documents,
        summary_text=summary_text,
        audio_b64=audio_b64,
    )
