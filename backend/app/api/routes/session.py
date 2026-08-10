"""
Jan Vaani — Session Routes
POST /sessions        → create session
GET  /sessions/{id}  → get session detail (history, profile, turns)
DELETE /sessions/{id} → end session
"""
import uuid
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.database import get_db
from app.models.db_models import Session as DBSession, UserProfileSlot, ConversationTurn, HandoffRequest, User
from app.models.schemas import SessionCreate, SessionResponse, SessionDetailResponse, ProfileSlotOut, TurnOut
from app.core.state_machine import get_state_machine, remove_state_machine
from app.core.slot_manager import get_slot_manager, remove_slot_manager
from app.core.auth import get_optional_user
from app.utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter()


@router.post("", response_model=SessionResponse, status_code=201)
async def create_session(
    payload: SessionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user),
):
    """Create a new user session. Returns session_id."""
    session_id = str(uuid.uuid4())
    db_session = DBSession(
        session_id=session_id,
        language=payload.language,
        status="active",
        current_state="IDLE",
        user_id=current_user.user_id if current_user else None,
    )
    db.add(db_session)
    await db.commit()
    await db.refresh(db_session)

    # Initialize in-memory state machine and slot manager
    get_state_machine(session_id)
    get_slot_manager(session_id)

    logger.info(f"Session created: {session_id} [{payload.language}] user={current_user.email if current_user else 'anonymous'}")
    return db_session


@router.get("/{session_id}", response_model=SessionDetailResponse)
async def get_session(
    session_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get full session detail including profile slots, turn history, and handoffs."""
    result = await db.execute(select(DBSession).where(DBSession.session_id == session_id))
    db_session = result.scalar_one_or_none()
    if not db_session:
        raise HTTPException(status_code=404, detail="Session not found.")

    # Profile slots
    slots_result = await db.execute(
        select(UserProfileSlot).where(UserProfileSlot.session_id == session_id)
    )
    slots = slots_result.scalars().all()

    # Conversation turns
    turns_result = await db.execute(
        select(ConversationTurn)
        .where(ConversationTurn.session_id == session_id)
        .order_by(ConversationTurn.turn_number)
    )
    turns = turns_result.scalars().all()

    # Handoffs
    handoffs_result = await db.execute(
        select(HandoffRequest).where(HandoffRequest.session_id == session_id)
    )
    handoffs = [
        {
            "handoff_id": h.handoff_id,
            "reason": h.reason,
            "summary_json": h.summary_json,
            "created_at": h.created_at.isoformat(),
        }
        for h in handoffs_result.scalars().all()
    ]

    return SessionDetailResponse(
        session=db_session,
        profile=[ProfileSlotOut.model_validate(s) for s in slots],
        turns=[TurnOut.model_validate(t) for t in turns],
        handoffs=handoffs,
    )


@router.delete("/{session_id}", status_code=204)
async def end_session(
    session_id: str,
    db: AsyncSession = Depends(get_db),
):
    """End a session (mark as completed)."""
    result = await db.execute(select(DBSession).where(DBSession.session_id == session_id))
    db_session = result.scalar_one_or_none()
    if not db_session:
        raise HTTPException(status_code=404, detail="Session not found.")

    db_session.status = "completed"
    await db.commit()

    remove_state_machine(session_id)
    remove_slot_manager(session_id)
    logger.info(f"Session ended: {session_id}")
