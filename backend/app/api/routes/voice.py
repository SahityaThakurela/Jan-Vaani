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
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.database import get_db, AsyncSessionLocal
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
# TEMPORARILY COMMENTED OUT — deterministic rules engine disabled
# from app.services.eligibility_engine import evaluate_eligibility
# from app.services.scheme_matcher import run_cross_scheme_match
from app.services.qdrant_service import qdrant_service
from app.utils.audio_utils import audio_bytes_to_base64
from app.utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter()

HANDOFF_CONFIDENCE_THRESHOLD = 0.45
MAX_LOW_CONF_TURNS = 3

# Common user profile fields extracted from every turn
UNIVERSAL_PROFILE_SLOTS = [
    {"slot_name": "age",        "slot_type": "number", "question_text_en": "What is the user's age in years?"},
    {"slot_name": "gender",     "slot_type": "string", "question_text_en": "What is the user's gender? (male/female/other)"},
    {"slot_name": "income",     "slot_type": "number", "question_text_en": "What is the user's annual household income in rupees?"},
    {"slot_name": "land_acres", "slot_type": "number", "question_text_en": "How many acres of land does the user own?"},
    {"slot_name": "caste",      "slot_type": "string", "question_text_en": "What is the user's caste category? (general/obc/sc/st)"},
    {"slot_name": "state",      "slot_type": "string", "question_text_en": "Which Indian state does the user belong to?"},
    {"slot_name": "occupation", "slot_type": "string", "question_text_en": "What is the user's occupation? (farmer/laborer/self-employed/etc)"},
    {"slot_name": "name",       "slot_type": "string", "question_text_en": "What is the user's full name?"},
    {"slot_name": "family_size","slot_type": "number", "question_text_en": "How many members are in the user's family?"},
    {"slot_name": "bpl_status", "slot_type": "boolean","question_text_en": "Is the user below poverty line (BPL)? (true/false)"},
]

async def _generate_and_save_title(session_id: str, user_text: str, language: str):
    """Background task to generate and save a session title."""
    title = await llm_service.generate_session_title(user_text, language)
    async with AsyncSessionLocal() as db:
        session_result = await db.execute(select(DBSession).where(DBSession.session_id == session_id))
        db_session = session_result.scalar_one_or_none()
        if db_session:
            db_session.title = title
            await db.commit()


@router.post("/turn", response_model=VoiceTurnResponse)
async def voice_turn(
    background_tasks: BackgroundTasks,
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

    if not db_session.title and turn_number == 1:
        background_tasks.add_task(_generate_and_save_title, session_id, user_text, language)

    # ── 2. State machine routing ──────────────────────────────
    agent_text = ""
    action_taken = "IDLE"
    intent_detected = None
    slots_extracted: Dict[str, Any] = {}
    eligibility_result: Optional[EligibilityResult] = None
    cross_matches: List[CrossSchemeMatch] = []
    handoff_triggered = False

    # Get conversation history for context — fetch BOTH user & agent turns in order
    turns_result = await db.execute(
        select(ConversationTurn)
        .where(ConversationTurn.session_id == session_id)
        .order_by(ConversationTurn.turn_number.asc())
        .limit(10)   # last 10 DB rows = up to 5 full exchanges
    )
    raw_turns = turns_result.scalars().all()
    # Build alternating user/agent history list (preserves full conversation memory)
    recent_turns = []
    for t in raw_turns:
        if t.user_text:
            recent_turns.append({"role": "user", "text": t.user_text})
        if t.agent_text:
            recent_turns.append({"role": "agent", "text": t.agent_text})

    try:
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
                    conversation_history=recent_turns,
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
                    conversation_history=recent_turns,
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
            # Fetch Qdrant context to enrich the AI reply
            try:
                chunks = await qdrant_service.search_schemes(user_text, language, limit=3)
            except Exception as qdrant_err:
                logger.warning(f"Qdrant search failed (non-critical): {qdrant_err}")
                chunks = []
            action_taken = "SEARCH_SCHEMES"
            summaries = [c["text"][:150] for c in chunks[:2]] if chunks else []
            agent_text = await llm_service.compose_reply(
                "search_result",
                {"query": user_text, "results": summaries},
                language,
                conversation_history=recent_turns,
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
                try:
                    chunks = await qdrant_service.search_schemes(
                        scheme_hint or user_text, language, limit=4, scheme_id_filter=resolved_id
                    )
                    context_texts = [c["text"] for c in chunks]
                except Exception as qdrant_err:
                    logger.warning(f"Qdrant search failed (non-critical): {qdrant_err}")
                    context_texts = []
                agent_text = await llm_service.compose_reply(
                    "scheme_detail",
                    {"scheme_id": resolved_id, "chunks": context_texts[:2]},
                    language,
                    conversation_history=recent_turns,
                )
                action_taken = f"SCHEME_DETAIL:{resolved_id}"
            else:
                agent_text = await llm_service.compose_reply(
                    "error",
                    {"message": "scheme not found", "hint": scheme_hint},
                    language,
                    conversation_history=recent_turns,
                )
                action_taken = "SCHEME_NOT_FOUND"

        # ── ELIGIBILITY CHECK — Direct AI response (rules engine DISABLED) ──
        elif intent_detected == llm_service.INTENT_ELIGIBILITY:
            sm.transition(SessionState.ELIGIBILITY_CHECK)
            action_taken = "ELIGIBILITY_CHECK:DIRECT_AI"

            # Resolve target scheme if not already set
            if not sm.target_scheme_id and scheme_hint:
                try:
                    all_schemes = await _get_all_schemes_brief(db)
                    sm.target_scheme_id = await llm_service.resolve_scheme_name(
                        scheme_hint, all_schemes, language
                    )
                except Exception as resolve_err:
                    logger.warning(f"Scheme resolution failed (non-critical): {resolve_err}")

            # Fetch Qdrant context for scheme if we know the target
            scheme_context: List[str] = []
            try:
                if sm.target_scheme_id:
                    chunks = await qdrant_service.search_schemes(
                        user_text, language, limit=4, scheme_id_filter=sm.target_scheme_id
                    )
                else:
                    chunks = await qdrant_service.search_schemes(user_text, language, limit=3)
                scheme_context = [c["text"][:300] for c in chunks[:3]]
            except Exception as qdrant_err:
                logger.warning(f"Qdrant context fetch failed (non-critical): {qdrant_err}")

            # NOTE: Deterministic eligibility engine and cross-scheme matcher are
            # TEMPORARILY DISABLED. The AI answers directly based on user query
            # and any available Qdrant knowledge context.
            #
            # DISABLED CODE (do not delete — will be re-enabled later):
            # required_slots = await _get_scheme_slots(db, sm.target_scheme_id)
            # missing_slots = slot_mgr.get_missing_slots(required_slots)
            # extracted = await llm_service.extract_slots(user_text, missing_slots or required_slots, language)
            # slot_mgr.fill_slots_from_dict(extracted, confidence=0.9, source_turn_id=turn_id)
            # slots_extracted = extracted
            # remaining_missing = slot_mgr.get_missing_slots(required_slots)
            # ... (slot collection loop)
            # rules_data = await _get_scheme_rules(db, sm.target_scheme_id)
            # decision = evaluate_eligibility(scheme_id=..., rules=rules_data, ...)
            # cross_decisions = await run_cross_scheme_match(profile=profile, db=db, ...)

            # Compose a direct AI response that answers the user's question
            agent_text = await llm_service.compose_reply(
                "eligibility_result",
                {
                    "user_query": user_text,
                    "scheme_id": sm.target_scheme_id,
                    "scheme_hint": scheme_hint,
                    "context": scheme_context,
                    "note": "Answer the user's question directly and helpfully based on the context provided.",
                },
                language,
                conversation_history=recent_turns,
            )

        else:
            # UNCLEAR intent — direct AI clarification
            agent_text = await llm_service.compose_reply(
                "clarify",
                {"message": user_text, "hint": "Respond helpfully to the user's query about government schemes."},
                language,
                conversation_history=recent_turns,
            )
            action_taken = "UNCLEAR"

    except Exception as pipeline_err:
        # ── Global fallback: any pipeline failure → direct Gemini Flash call ──
        logger.error(f"[{session_id}] Pipeline error, falling back to direct AI: {pipeline_err}", exc_info=True)
        try:
            agent_text = await _direct_ai_response(user_text, language)
            action_taken = "DIRECT_AI_FALLBACK"
        except Exception as ai_err:
            logger.error(f"[{session_id}] Direct AI fallback also failed: {ai_err}")
            agent_text = (
                "Aapka sawaal sun liya. Kripya thoda wait karein aur dobara try karein."
                if language == "hi"
                else "Your question was heard. Please wait a moment and try again."
            )

    # ── 3. TTS (Rime Coda) ─────────────────────────────────────
    audio_out = await tts_service.synthesize_speech(agent_text, language)
    audio_b64 = audio_bytes_to_base64(audio_out) if audio_out else ""

    # ── 4. Universal profile slot extraction (runs every turn) ──
    # Extract common profile facts from the user's utterance regardless of intent.
    # This runs even when the deterministic eligibility engine is disabled.
    try:
        universal_extracted = await llm_service.extract_slots(
            user_text, UNIVERSAL_PROFILE_SLOTS, language
        )
        if universal_extracted:
            slot_mgr.fill_slots_from_dict(universal_extracted, confidence=0.85, source_turn_id=turn_id)
            # Merge into slots_extracted so the frontend receives them in this response
            slots_extracted = {**slots_extracted, **universal_extracted}
            logger.info(f"[{session_id}] Universal slots extracted: {list(universal_extracted.keys())}")
    except Exception as slot_err:
        logger.warning(f"[{session_id}] Universal slot extraction failed (non-critical): {slot_err}")

    # ── 5. Persist turn + slots ────────────────────────────────
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


async def _get_scheme_slots(db: AsyncSession, scheme_id: str) -> List[Dict[str, Any]]:
    result = await db.execute(
        select(SchemeRequiredSlot)
        .where(SchemeRequiredSlot.scheme_id == scheme_id)
        .order_by(SchemeRequiredSlot.priority)
    )
    rows = result.scalars().all()
    return [
        {
            "slot_name": r.slot_name,
            "slot_type": r.slot_type,
            "question_text_en": r.question_text_en,
            "question_text_hi": r.question_text_hi,
            "priority": r.priority,
        }
        for r in rows
    ]


async def _get_scheme_rules(db: AsyncSession, scheme_id: str) -> List[Dict[str, Any]]:
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


async def _direct_ai_response(user_text: str, language: str = "hi") -> str:
    """
    Direct Gemini Flash call — bypasses all state machine / rules engine logic.
    Used as the global fallback when any part of the pipeline fails.
    Also used for ELIGIBILITY_CHECK intent while the deterministic engine is disabled.
    """
    import google.generativeai as genai
    from app.config import settings

    if not user_text:
        return (
            "Kripya apna sawaal dobara poochhen."
            if language == "hi"
            else "Please ask your question again."
        )

    try:
        genai.configure(api_key=settings.gemini_api_key)
        model = genai.GenerativeModel(
            model_name=settings.gemini_model,
            system_instruction=(
                "You are Jan Vaani, a helpful voice assistant for rural Indian users. "
                "You help them understand Indian government welfare schemes (yojanas) like PM-KISAN, "
                "Pradhan Mantri Awas Yojana, Ayushman Bharat, MGNREGA, etc. "
                "Always respond in the same language the user used (Hindi or English). "
                "Be concise (1-3 sentences), warm, and use simple spoken language. "
                "No bullet points, no markdown — this is audio output."
            ),
            generation_config=genai.GenerationConfig(
                temperature=0.3,
                max_output_tokens=256,
            ),
        )
        response = await model.generate_content_async(user_text)
        return response.text.strip()
    except Exception as e:
        logger.error(f"_direct_ai_response failed: {e}")
        return (
            "Aapka sawaal sun liya. Abhi kuch takneeki dikkat aa rahi hai, thodi der mein try karein."
            if language == "hi"
            else "Your question was heard. There's a temporary issue — please try again shortly."
        )
