"""
Jan Vaani — Session Routes
GET  /sessions        → list sessions for authenticated user
POST /sessions        → create session
GET  /sessions/{id}  → get session detail (history, profile, turns)
DELETE /sessions/{id} → end session
"""
import uuid
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.db.database import get_db
from app.models.db_models import Session as DBSession, UserProfileSlot, ConversationTurn, HandoffRequest, User
from app.models.schemas import SessionCreate, SessionResponse, SessionDetailResponse, ProfileSlotOut, TurnOut
from app.core.state_machine import get_state_machine, remove_state_machine
from app.core.slot_manager import get_slot_manager, remove_slot_manager
from app.core.auth import get_optional_user, get_current_user
from app.utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter()


@router.get("", tags=["Sessions"])
async def list_sessions(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all sessions for the authenticated user, newest first, with turn counts."""
    result = await db.execute(
        select(DBSession)
        .where(DBSession.user_id == current_user.user_id)
        .order_by(DBSession.created_at.desc())
    )
    sessions = result.scalars().all()

    session_list = []
    for s in sessions:
        turns_count_result = await db.execute(
            select(func.count(ConversationTurn.turn_id))
            .where(ConversationTurn.session_id == s.session_id)
        )
        turn_count = turns_count_result.scalar() or 0
        session_list.append({
            "session_id": s.session_id,
            "language": s.language,
            "status": s.status,
            "current_state": s.current_state,
            "created_at": s.created_at.isoformat(),
            "updated_at": s.updated_at.isoformat(),
            "turn_count": turn_count,
        })

    logger.info(f"Listed {len(session_list)} sessions for user {current_user.email}")
    return session_list


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


@router.patch("/{session_id}/reactivate", status_code=200)
async def reactivate_session(
    session_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Reactivate a session so the user can continue from where they left off."""
    result = await db.execute(
        select(DBSession).where(
            DBSession.session_id == session_id,
            DBSession.user_id == current_user.user_id,
        )
    )
    db_session = result.scalar_one_or_none()
    if not db_session:
        raise HTTPException(status_code=404, detail="Session not found.")

    db_session.status = "active"
    await db.commit()
    await db.refresh(db_session)

    # Re-initialize in-memory managers so voice turns work again
    get_state_machine(session_id)
    get_slot_manager(session_id)

    logger.info(f"Session reactivated: {session_id} by user {current_user.email}")
    return {"session_id": session_id, "status": "active"}

