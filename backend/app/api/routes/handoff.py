"""
Jan Vaani — Handoff Routes
POST /handoff/trigger  → manually trigger handoff
GET  /handoff/{id}     → get handoff summary (for human agent screen)
GET  /handoff/session/{session_id} → get all handoffs for a session
"""
import json
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.database import get_db
from app.models.db_models import HandoffRequest, Session as DBSession
from app.models.schemas import HandoffTriggerRequest, HandoffSummary
from app.core.state_machine import get_state_machine, SessionState
from app.core.slot_manager import get_slot_manager
from app.services import tts_service, llm_service
from app.utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter()


@router.post("/trigger")
async def trigger_handoff(
    payload: HandoffTriggerRequest,
    db: AsyncSession = Depends(get_db),
):
    """Manually trigger a handoff for a session."""
    session_result = await db.execute(
        select(DBSession).where(DBSession.session_id == payload.session_id)
    )
    db_session = session_result.scalar_one_or_none()
    if not db_session:
        raise HTTPException(status_code=404, detail="Session not found.")

    sm = get_state_machine(payload.session_id, db_session.current_state)
    slot_mgr = get_slot_manager(payload.session_id)
    await slot_mgr.load_from_db(db)

    profile = slot_mgr.get_profile()
    language = db_session.language

    summary = {
        "session_id": payload.session_id,
        "language": language,
        "target_scheme_id": sm.target_scheme_id,
        "profile": profile,
        "reason": payload.reason,
    }

    handoff = HandoffRequest(
        session_id=payload.session_id,
        reason=payload.reason,
        summary_json=json.dumps(summary, ensure_ascii=False),
    )
    db.add(handoff)
    sm.transition(SessionState.HANDOFF)
    db_session.current_state = SessionState.HANDOFF.value
    db_session.status = "handed_off"
    await db.commit()
    await db.refresh(handoff)

    agent_text = await llm_service.compose_reply(
        "handoff",
        {"reason": payload.reason, "profile": profile},
        language,
    )
    audio_bytes = await tts_service.synthesize_speech(agent_text, language)

    from app.utils.audio_utils import audio_bytes_to_base64
    return {
        "handoff_id": handoff.handoff_id,
        "session_id": payload.session_id,
        "agent_text": agent_text,
        "audio_b64": audio_bytes_to_base64(audio_bytes),
        "summary": summary,
    }


@router.get("/{handoff_id}")
async def get_handoff(
    handoff_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get handoff summary by ID — displayed on the human agent screen."""
    result = await db.execute(
        select(HandoffRequest).where(HandoffRequest.handoff_id == handoff_id)
    )
    handoff = result.scalar_one_or_none()
    if not handoff:
        raise HTTPException(status_code=404, detail="Handoff not found.")

    summary = json.loads(handoff.summary_json) if handoff.summary_json else {}
    return {
        "handoff_id": handoff.handoff_id,
        "session_id": handoff.session_id,
        "reason": handoff.reason,
        "summary": summary,
        "created_at": handoff.created_at.isoformat(),
    }


@router.get("/session/{session_id}")
async def get_session_handoffs(
    session_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get all handoffs for a session."""
    result = await db.execute(
        select(HandoffRequest).where(HandoffRequest.session_id == session_id)
    )
    handoffs = result.scalars().all()
    return [
        {
            "handoff_id": h.handoff_id,
            "reason": h.reason,
            "summary": json.loads(h.summary_json) if h.summary_json else {},
            "created_at": h.created_at.isoformat(),
        }
        for h in handoffs
    ]
