"""
Jan Vaani — Main Voice Pipeline Route

POST /voice/turn
  - Receives audio bytes (multipart)
  - Runs STT → State Machine → LLM/Engine/Qdrant → TTS
  - Returns transcript, agent text, audio (base64), next state

POST /voice/interrupt
  - Stops current agent turn and re-initializes session state
  - Preserves all filled profile slots
"""
import json
import uuid
from typing import Any, Dict, Optional
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.database import get_db
from app.models.db_models import (
    Session as DBSession, ConversationTurn,
    Scheme, SchemeEligibilityRule, SchemeRequiredSlot, HandoffRequest,
)
from app.models.schemas import (
    VoiceTurnResponse, InterruptRequest, InterruptResponse,
    EligibilityResult, CrossSchemeMatch,
)
from app.core.state_machine import get_state_machine, SessionState
from app.core.slot_manager import get_slot_manager
from app.services import stt_service, tts_service, llm_service
from app.services.eligibility_engine import evaluate_eligibility
from app.services.scheme_matcher import run_cross_scheme_match
from app.services.qdrant_service import qdrant_service
from app.utils.audio_utils import audio_bytes_to_base64
from app.utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter()

HANDOFF_CONFIDENCE_THRESHOLD = 0.45
MAX_LOW_CONF_TURNS = 3


@router.post("/turn", response_model=VoiceTurnResponse)
async def voice_turn(
    session_id: str = Form(...),
    language: str = Form(default="hi"),
    audio: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    """
    Main pipeline endpoint. Receives audio, processes through the full pipeline,
    returns transcript + agent reply + audio.
    """
    # ── 0. Validate session ────────────────────────────────────
    session_result = await db.execute(
        select(DBSession).where(DBSession.session_id == session_id)
    )
    db_session = session_result.scalar_one_or_none()
    if not db_session:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found.")

    sm = get_state_machine(session_id, db_session.current_state)
    slot_mgr = get_slot_manager(session_id)
    await slot_mgr.load_from_db(db)

    sm.increment_turn()
    turn_id = str(uuid.uuid4())
    turn_number = sm.turn_count

    # ── 1. STT ────────────────────────────────────────────────
    audio_bytes = await audio.read()
    mimetype = audio.content_type or "audio/webm"
    stt_result = await stt_service.transcribe_audio(audio_bytes, language, mimetype)
    user_text = stt_result["transcript"]
    stt_confidence = stt_result["confidence"]

    logger.info(f"[{session_id}] Turn {turn_number} — user: '{user_text[:80]}'")

    # ── 2. State machine routing ──────────────────────────────
    agent_text = ""
    action_taken = "IDLE"
    intent_detected = None
    slots_extracted: Dict[str, Any] = {}
    eligibility_result: Optional[EligibilityResult] = None
    cross_matches: list[CrossSchemeMatch] = []
    handoff_triggered = False

    # Get conversation history for context
    turns_result = await db.execute(
        select(ConversationTurn)
        .where(ConversationTurn.session_id == session_id)
        .order_by(ConversationTurn.turn_number.desc())
        .limit(5)
    )
    recent_turns = [
        {"role": "user", "text": t.user_text or ""}
        for t in turns_result.scalars().all()
    ]

    # ── 2a. Intent Classification ──────────────────────────────
    sm.transition(SessionState.INTENT_CLASSIFICATION)
    intent_data = await llm_service.classify_intent(user_text, language, recent_turns)
    intent_detected = intent_data.get("intent", llm_service.INTENT_UNCLEAR)
    scheme_hint = intent_data.get("scheme_hint")
    action_taken = f"INTENT:{intent_detected}"

    # Handle correction intent
    if intent_detected == llm_service.INTENT_CORRECTION:
        correction_field = intent_data.get("correction_field")
        correction_value = intent_data.get("correction_value")
        if correction_field and correction_value:
            slot_mgr.fill_slot(correction_field, correction_value, confidence=0.95, source_turn_id=turn_id)
            agent_text = await llm_service.compose_reply(
                "correction_ack",
                {"field": correction_field, "value": correction_value},
                language,
            )
            action_taken = f"CORRECTION:{correction_field}"
        else:
            # Try to re-extract from the whole utterance
            current_scheme_slots = await _get_scheme_slots(db, sm.target_scheme_id) if sm.target_scheme_id else []
            extracted = await llm_service.extract_slots(user_text, current_scheme_slots, language)
            slot_mgr.fill_slots_from_dict(extracted, confidence=0.85, source_turn_id=turn_id)
            slots_extracted = extracted
            agent_text = await llm_service.compose_reply(
                "correction_ack",
                {"extracted": extracted},
                language,
            )

    # Handle handoff intent
    elif intent_detected == llm_service.INTENT_HANDOFF:
        handoff_triggered = True
        agent_text, eligibility_result = await _trigger_handoff(
            session_id=session_id,
            db=db,
            sm=sm,
            slot_mgr=slot_mgr,
            reason="user_request",
            language=language,
        )
        action_taken = "HANDOFF"

    # Search schemes
    elif intent_detected == llm_service.INTENT_SEARCH:
        sm.transition(SessionState.SEARCH_SCHEMES)
        chunks = await qdrant_service.search_schemes(user_text, language, limit=3)
        action_taken = "SEARCH_SCHEMES"
        if chunks:
            summaries = [c["text"][:150] for c in chunks[:2]]
            agent_text = await llm_service.compose_reply(
                "search_result",
                {"query": user_text, "results": summaries},
                language,
            )
        else:
            agent_text = await llm_service.compose_reply(
                "search_result",
                {"query": user_text, "results": []},
                language,
            )

    # Scheme detail
    elif intent_detected == llm_service.INTENT_DETAIL:
        sm.transition(SessionState.SCHEME_DETAIL)
        # Resolve scheme name
        all_schemes = await _get_all_schemes_brief(db)
        resolved_id = await llm_service.resolve_scheme_name(
            scheme_hint or user_text, all_schemes, language
        )
        if resolved_id:
            sm.target_scheme_id = resolved_id
            chunks = await qdrant_service.search_schemes(
                scheme_hint or user_text, language, limit=4, scheme_id_filter=resolved_id
            )
            context_texts = [c["text"] for c in chunks]
            agent_text = await llm_service.compose_reply(
                "scheme_detail",
                {"scheme_id": resolved_id, "chunks": context_texts[:2]},
                language,
            )
            action_taken = f"SCHEME_DETAIL:{resolved_id}"
        else:
            agent_text = await llm_service.compose_reply(
                "error",
                {"message": "scheme not found", "hint": scheme_hint},
                language,
            )
            action_taken = "SCHEME_NOT_FOUND"

    # Eligibility check
    elif intent_detected == llm_service.INTENT_ELIGIBILITY:
        sm.transition(SessionState.ELIGIBILITY_CHECK)

        # Resolve target scheme if not already set
        if not sm.target_scheme_id and scheme_hint:
            all_schemes = await _get_all_schemes_brief(db)
            sm.target_scheme_id = await llm_service.resolve_scheme_name(
                scheme_hint, all_schemes, language
            )

        if not sm.target_scheme_id:
            # Ask user which scheme
            agent_text = await llm_service.compose_reply(
                "clarify",
                {"message": "Which scheme would you like to check eligibility for?"},
                language,
            )
            action_taken = "CLARIFY_SCHEME"
        else:
            # Get required slots for target scheme
            required_slots = await _get_scheme_slots(db, sm.target_scheme_id)

            # Extract slots from current utterance
            missing_slots = slot_mgr.get_missing_slots(required_slots)
            extracted = await llm_service.extract_slots(user_text, missing_slots or required_slots, language)
            slot_mgr.fill_slots_from_dict(extracted, confidence=0.9, source_turn_id=turn_id)
            slots_extracted = extracted

            # Check if we have all slots
            remaining_missing = slot_mgr.get_missing_slots(required_slots)

            if remaining_missing:
                # Track low-confidence turns
                if stt_confidence < HANDOFF_CONFIDENCE_THRESHOLD and not extracted:
                    sm.mark_low_confidence()
                else:
                    sm.reset_low_confidence()

                # Auto-handoff if too many low-confidence turns
                if sm.should_trigger_handoff():
                    handoff_triggered = True
                    agent_text, eligibility_result = await _trigger_handoff(
                        session_id=session_id, db=db, sm=sm,
                        slot_mgr=slot_mgr, reason="low_confidence", language=language,
                    )
                    action_taken = "HANDOFF:LOW_CONFIDENCE"
                else:
                    # Ask next slot
                    next_slot = remaining_missing[0]
                    question_key = "question_text_hi" if language == "hi" else "question_text_en"
                    question = next_slot.get(question_key, next_slot.get("question_text_en", ""))
                    agent_text = await llm_service.compose_reply(
                        "ask_slot",
                        {"slot": next_slot["slot_name"], "question": question},
                        language,
                    )
                    action_taken = f"ASK_SLOT:{next_slot['slot_name']}"
            else:
                # All slots filled — run eligibility engine
                sm.transition(SessionState.RESULT)
                profile = slot_mgr.get_profile()

                # Fetch rules for target scheme
                rules_data = await _get_scheme_rules(db, sm.target_scheme_id)
                scheme_name = await _get_scheme_name(db, sm.target_scheme_id, language)
                slot_names = [s["slot_name"] for s in required_slots]

                decision = evaluate_eligibility(
                    scheme_id=sm.target_scheme_id,
                    scheme_name=scheme_name,
                    rules=rules_data,
                    required_slots=slot_names,
                    profile=profile,
                )

                eligibility_result = EligibilityResult(
                    scheme_id=decision.scheme_id,
                    scheme_name=decision.scheme_name,
                    eligible=decision.eligible,
                    matched_rules=decision.matched_rules,
                    total_rules=decision.total_rules,
                    failed_rules=[
                        {"field": r.field_name, "reason": r.reason}
                        for r in decision.failed_rules
                    ],
                    missing_slots=decision.missing_slots,
                    explanation=decision.explanation,
                )

                # Run cross-scheme matcher
                cross_decisions = await run_cross_scheme_match(
                    profile=profile, db=db, exclude_scheme_id=sm.target_scheme_id
                )
                cross_matches = [
                    CrossSchemeMatch(
                        scheme_id=d.scheme_id,
                        scheme_name=d.scheme_name,
                        eligible=d.eligible,
                        matched_rules=d.matched_rules,
                        total_rules=d.total_rules,
                    )
                    for d in cross_decisions[:3]
                ]

                # Store case in Qdrant memory
                try:
                    await qdrant_service.upsert_case_memory(
                        session_id=session_id, profile=profile,
                        scheme_id=sm.target_scheme_id, eligible=decision.eligible, language=language,
                    )
                except Exception as e:
                    logger.warning(f"Case memory upsert failed (non-critical): {e}")

                # Compose spoken result
                eligible_cross = [c for c in cross_decisions if c.eligible and c.scheme_id != sm.target_scheme_id]
                agent_text = await llm_service.compose_reply(
                    "eligibility_result",
                    {
                        "explanation": decision.explanation,
                        "eligible": decision.eligible,
                        "other_schemes": [c.scheme_name for c in eligible_cross[:2]],
                    },
                    language,
                )
                action_taken = f"ELIGIBILITY_RESULT:{'ELIGIBLE' if decision.eligible else 'NOT_ELIGIBLE'}"

                # Borderline: trigger handoff if barely failed
                if not decision.eligible and decision.matched_rules >= decision.total_rules - 1:
                    handoff_triggered = True
                    _, _ = await _trigger_handoff(
                        session_id=session_id, db=db, sm=sm,
                        slot_mgr=slot_mgr, reason="borderline", language=language,
                    )
                    action_taken += ":BORDERLINE_HANDOFF"

    else:
        # UNCLEAR intent
        agent_text = await llm_service.compose_reply(
            "clarify",
            {"message": "I didn't understand. Please try again."},
            language,
        )
        action_taken = "UNCLEAR"

    # ── 3. TTS (Rime Coda) ─────────────────────────────────────
    audio_out = await tts_service.synthesize_speech(agent_text, language)
    audio_b64 = audio_bytes_to_base64(audio_out) if audio_out else ""

    # ── 4. Persist turn + slots ────────────────────────────────
    db.add(ConversationTurn(
        turn_id=turn_id,
        session_id=session_id,
        turn_number=turn_number,
        user_text=user_text,
        agent_text=agent_text,
        action_taken=action_taken,
        intent_detected=intent_detected,
        slots_extracted=json.dumps(slots_extracted, ensure_ascii=False) if slots_extracted else None,
        was_interrupted=sm.is_interrupted,
    ))
    # Update session state
    db_session.current_state = sm.state.value
    db_session.current_scheme_id = sm.target_scheme_id
    await db.commit()
    await slot_mgr.persist_to_db(db)

    logger.info(f"[{session_id}] Turn {turn_number} done. State→{sm.state}. Action: {action_taken}")

    return VoiceTurnResponse(
        session_id=session_id,
        turn_id=turn_id,
        user_transcript=user_text,
        agent_text=agent_text,
        audio_b64=audio_b64,
        next_state=sm.state.value,
        action_taken=action_taken,
        intent_detected=intent_detected,
        slots_extracted=slots_extracted or None,
        eligibility_result=eligibility_result,
        handoff_triggered=handoff_triggered,
        cross_scheme_matches=cross_matches or None,
    )


@router.post("/interrupt", response_model=InterruptResponse)
async def interrupt_voice(
    payload: InterruptRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    'Tap to Interrupt' — resets current intent/turn state, preserves all filled slots.
    The user can then issue a new request from scratch.
    """
    session_result = await db.execute(
        select(DBSession).where(DBSession.session_id == payload.session_id)
    )
    db_session = session_result.scalar_one_or_none()
    if not db_session:
        raise HTTPException(status_code=404, detail=f"Session '{payload.session_id}' not found.")

    sm = get_state_machine(payload.session_id, db_session.current_state)
    sm.interrupt()

    db_session.current_state = SessionState.IDLE.value
    db_session.current_scheme_id = None
    await db.commit()

    logger.info(f"[{payload.session_id}] Interrupt: session reset to IDLE, slots preserved.")
    return InterruptResponse(
        session_id=payload.session_id,
        message="Session interrupted. Your collected information has been saved. Please start a new request.",
        new_state=SessionState.IDLE.value,
    )


# ── Helpers ───────────────────────────────────────────────────
async def _get_all_schemes_brief(db: AsyncSession):
    result = await db.execute(select(Scheme))
    schemes = result.scalars().all()
    return [
        {
            "scheme_id": s.scheme_id,
            "name_en": s.name_en,
            "name_hi": s.name_hi,
            "aliases": s.aliases or "",
        }
        for s in schemes
    ]


async def _get_scheme_slots(db: AsyncSession, scheme_id: str) -> list[dict]:
    result = await db.execute(
        select(SchemeRequiredSlot)
        .where(SchemeRequiredSlot.scheme_id == scheme_id)
        .order_by(SchemeRequiredSlot.priority)
    )
    return [
        {
            "slot_name": s.slot_name,
            "slot_type": s.slot_type,
            "question_text_en": s.question_text_en,
            "question_text_hi": s.question_text_hi,
            "priority": s.priority,
        }
        for s in result.scalars().all()
    ]


async def _get_scheme_rules(db: AsyncSession, scheme_id: str) -> list[dict]:
    result = await db.execute(
        select(SchemeEligibilityRule).where(SchemeEligibilityRule.scheme_id == scheme_id)
    )
    return [
        {
            "field_name": r.field_name,
            "operator": r.operator,
            "value": r.value,
            "value_type": r.value_type,
        }
        for r in result.scalars().all()
    ]


async def _get_scheme_name(db: AsyncSession, scheme_id: str, language: str = "hi") -> str:
    result = await db.execute(select(Scheme).where(Scheme.scheme_id == scheme_id))
    scheme = result.scalar_one_or_none()
    if not scheme:
        return scheme_id
    return scheme.name_hi if language == "hi" else scheme.name_en


async def _trigger_handoff(
    session_id: str,
    db: AsyncSession,
    sm,
    slot_mgr,
    reason: str,
    language: str,
) -> tuple[str, Optional[EligibilityResult]]:
    """Create a handoff record and compose the handoff message."""
    import json as _json

    sm.transition(SessionState.HANDOFF)
    profile = slot_mgr.get_profile()

    summary = {
        "session_id": session_id,
        "language": language,
        "target_scheme_id": sm.target_scheme_id,
        "profile": profile,
        "reason": reason,
    }

    handoff = HandoffRequest(
        session_id=session_id,
        reason=reason,
        summary_json=_json.dumps(summary, ensure_ascii=False),
    )
    db.add(handoff)
    await db.commit()

    agent_text = await llm_service.compose_reply("handoff", {"reason": reason, "profile": profile}, language)
    return agent_text, None
