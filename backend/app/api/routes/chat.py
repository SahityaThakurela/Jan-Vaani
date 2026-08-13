"""
Jan Vaani — Text Chat Route (Profile Questionnaire)

POST /chat/turn
  - Accepts plain text message (no audio)
  - Drives a 7-question profile questionnaire via LLM
  - After all questions: returns a markdown summary table
  - Also persists slots to the session's slot manager
"""
import json
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.database import get_db
from app.models.db_models import Session as DBSession, ConversationTurn
from app.models.schemas import ChatTurnRequest, ChatTurnResponse
from app.core.slot_manager import get_slot_manager
from app.services import llm_service, tts_service
from app.utils.audio_utils import audio_bytes_to_base64
from app.utils.logger import get_logger
import uuid

logger = get_logger(__name__)
router = APIRouter()


# ── Questionnaire definition ──────────────────────────────────────────────────

QUESTIONS: List[Dict[str, Any]] = [
    {
        "slot_name": "name",
        "slot_type": "string",
        "question_hi": "नमस्ते! मैं जन वाणी हूँ। शुरुआत करने के लिए — आपका पूरा नाम क्या है?",
        "question_en": "Hello! I'm Jan Vaani. To get started — what is your full name?",
        "question_text_en": "What is the user's full name?",
    },
    {
        "slot_name": "age",
        "slot_type": "number",
        "question_hi": "धन्यवाद, {name}! आपकी उम्र कितनी है?",
        "question_en": "Thank you, {name}! How old are you?",
        "question_text_en": "What is the user's age in years?",
    },
    {
        "slot_name": "gender",
        "slot_type": "string",
        "question_hi": "आप पुरुष हैं, महिला हैं, या अन्य?",
        "question_en": "Are you male, female, or other?",
        "question_text_en": "What is the user's gender? (male/female/other)",
    },
    {
        "slot_name": "state",
        "slot_type": "string",
        "question_hi": "आप किस राज्य में रहते हैं?",
        "question_en": "Which state do you live in?",
        "question_text_en": "Which Indian state does the user live in?",
    },
    {
        "slot_name": "occupation",
        "slot_type": "string",
        "question_hi": "आपका पेशा क्या है? (जैसे — किसान, मजदूर, व्यापारी, सरकारी कर्मचारी)",
        "question_en": "What is your occupation? (e.g. farmer, labourer, trader, govt employee)",
        "question_text_en": "What is the user's occupation?",
    },
    {
        "slot_name": "income",
        "slot_type": "number",
        "question_hi": "आपकी सालाना पारिवारिक आमदनी कितनी है? (रुपयों में बताएं)",
        "question_en": "What is your annual household income? (in rupees)",
        "question_text_en": "What is the user's annual household income in rupees?",
    },
    {
        "slot_name": "caste",
        "slot_type": "string",
        "question_hi": "आपकी जाति श्रेणी क्या है? (सामान्य / OBC / SC / ST)",
        "question_en": "What is your caste category? (General / OBC / SC / ST)",
        "question_text_en": "What is the user's caste category? (general/obc/sc/st)",
    },
]

# In-memory questionnaire state: { session_id -> { state, current_q, collected } }
_QUESTIONNAIRE_STATE: Dict[str, Dict[str, Any]] = {}

STATE_GREETING = "GREETING"
STATE_COLLECTING = "COLLECTING"
STATE_COMPLETE = "COMPLETE"


# ── Helpers ───────────────────────────────────────────────────────────────────

def _get_q_state(session_id: str) -> Dict[str, Any]:
    if session_id not in _QUESTIONNAIRE_STATE:
        _QUESTIONNAIRE_STATE[session_id] = {
            "state": STATE_GREETING,
            "current_q": 0,
            "collected": {},
        }
    return _QUESTIONNAIRE_STATE[session_id]


def _format_question(q: Dict[str, Any], collected: Dict[str, Any], language: str) -> str:
    """Return localised question string, interpolating collected slots into the text."""
    raw = q["question_hi"] if language == "hi" else q["question_en"]
    try:
        return raw.format(**collected)
    except KeyError:
        return raw


def _build_summary_table(collected: Dict[str, Any], language: str) -> str:
    """Build a markdown table + brief paragraph from collected slots."""

    if language == "hi":
        header = "| जानकारी | आपका जवाब |\n|---------|------------|"
        labels = {
            "name":       "नाम",
            "age":        "उम्र",
            "gender":     "लिंग",
            "state":      "राज्य",
            "occupation": "पेशा",
            "income":     "सालाना आमदनी (₹)",
            "caste":      "जाति श्रेणी",
        }
        intro = "✅ बहुत अच्छा! यहाँ आपकी दी गई जानकारी का सारांश है:\n\n"
        outro = (
            "\n\n💡 अब आप पूछ सकते हैं: \"मेरे लिए कौन सी सरकारी योजनाएं हैं?\" "
            "— माइक दबाएं या नीचे टाइप करें।"
        )
    else:
        header = "| Field | Your Answer |\n|-------|-------------|"
        labels = {
            "name":       "Name",
            "age":        "Age",
            "gender":     "Gender",
            "state":      "State",
            "occupation": "Occupation",
            "income":     "Annual Income (₹)",
            "caste":      "Caste Category",
        }
        intro = "✅ Great! Here's a summary of the information you provided:\n\n"
        outro = (
            "\n\n💡 Now you can ask: \"Which government schemes am I eligible for?\" "
            "— press the mic or type below."
        )

    rows = []
    for q in QUESTIONS:
        key = q["slot_name"]
        val = collected.get(key, "—")
        label = labels.get(key, key)
        rows.append(f"| {label} | {val} |")

    table = header + "\n" + "\n".join(rows)
    return intro + table + outro


# ── Route ─────────────────────────────────────────────────────────────────────

@router.post("/turn", response_model=ChatTurnResponse)
async def chat_turn(
    payload: ChatTurnRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Drive the profile-collection questionnaire via text chat.
    Returns the next question or a formatted summary table when complete.
    """
    session_id = payload.session_id
    language = payload.language
    user_message = payload.message.strip()

    # Validate session exists
    session_result = await db.execute(
        select(DBSession).where(DBSession.session_id == session_id)
    )
    db_session = session_result.scalar_one_or_none()
    if not db_session:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found.")

    # Load slot manager for persistence
    slot_mgr = get_slot_manager(session_id)
    await slot_mgr.load_from_db(db)

    q_state = _get_q_state(session_id)
    turn_id = str(uuid.uuid4())
    slots_extracted: Dict[str, Any] = {}
    table_markdown: Optional[str] = None

    # ── If we already completed the questionnaire, re-show the summary ────────
    if q_state["state"] == STATE_COMPLETE:
        table_markdown = _build_summary_table(q_state["collected"], language)
        agent_text = (
            "आपकी प्रोफ़ाइल पहले से पूरी हो चुकी है। यहाँ आपकी जानकारी है:"
            if language == "hi"
            else "Your profile is already complete. Here is your information:"
        )
        _persist_turn(db, session_id, turn_id, user_message, agent_text)
        await db.commit()
        return ChatTurnResponse(
            session_id=session_id,
            agent_text=agent_text,
            next_state=STATE_COMPLETE,
            current_question=None,
            slots_extracted=None,
            table_markdown=table_markdown,
        )

    # ── GREETING state: user sent first message, ask Q1 ──────────────────────
    if q_state["state"] == STATE_GREETING:
        q_state["state"] = STATE_COLLECTING
        q_state["current_q"] = 0
        agent_text = _format_question(QUESTIONS[0], q_state["collected"], language)
        _persist_turn(db, session_id, turn_id, user_message, agent_text)
        await db.commit()

        # ── TTS for greeting (when requested) ────────────────────────────────
        audio_b64: Optional[str] = None
        if payload.with_audio:
            try:
                audio_bytes = await tts_service.synthesize_speech(agent_text, language)
                audio_b64 = audio_bytes_to_base64(audio_bytes) if audio_bytes else None
                logger.info(f"[{session_id}] Greeting TTS synthesized: {len(agent_text)} chars")
            except Exception as tts_err:
                logger.warning(f"[{session_id}] Greeting TTS failed (non-critical): {tts_err}")

        return ChatTurnResponse(
            session_id=session_id,
            agent_text=agent_text,
            next_state=STATE_COLLECTING,
            current_question=1,
            audio_b64=audio_b64,
        )

    # ── COLLECTING state: extract answer, advance question ────────────────────
    current_q_idx = q_state["current_q"]
    current_q_def = QUESTIONS[current_q_idx]

    # Extract slot value from user's reply using LLM
    try:
        extracted = await llm_service.extract_slots(
            user_message,
            [current_q_def],
            language,
        )
        if extracted:
            key = current_q_def["slot_name"]
            val = extracted.get(key)
            if val:
                q_state["collected"][key] = val
                slots_extracted[key] = val
                # Persist to slot manager
                slot_mgr.fill_slot(key, str(val), confidence=0.9, source_turn_id=turn_id)
                logger.info(f"[{session_id}] Chat Q{current_q_idx+1} extracted: {key}={val}")
    except Exception as e:
        logger.warning(f"[{session_id}] Slot extraction failed (non-critical): {e}")

    # Move to next question
    next_q_idx = current_q_idx + 1
    q_state["current_q"] = next_q_idx

    if next_q_idx >= len(QUESTIONS):
        # ── All questions answered → generate summary table ───────────────────
        q_state["state"] = STATE_COMPLETE
        table_markdown = _build_summary_table(q_state["collected"], language)
        agent_text = (
            "सभी सवाल हो गए! नीचे आपकी जानकारी का सारांश देखें।"
            if language == "hi"
            else "All done! See your profile summary below."
        )
        next_state = STATE_COMPLETE
        current_question = None
    else:
        # ── Ask next question ─────────────────────────────────────────────────
        next_q_def = QUESTIONS[next_q_idx]
        agent_text = _format_question(next_q_def, q_state["collected"], language)
        next_state = STATE_COLLECTING
        current_question = next_q_idx + 1  # 1-based for frontend display

    # Persist turn to DB
    _persist_turn(db, session_id, turn_id, user_message, agent_text)
    await db.commit()
    await slot_mgr.persist_to_db(db)

    # ── Optional TTS synthesis (when called from voice mode) ──────────────────
    audio_b64: Optional[str] = None
    if payload.with_audio and agent_text:
        try:
            # For the summary table, speak only the intro text (not the table rows)
            speak_text = agent_text
            if table_markdown:
                # Strip the table — speak only the first line
                speak_text = agent_text.split('\n')[0].strip()
            audio_bytes = await tts_service.synthesize_speech(speak_text, language)
            audio_b64 = audio_bytes_to_base64(audio_bytes) if audio_bytes else None
        except Exception as tts_err:
            logger.warning(f"[{session_id}] Chat TTS failed (non-critical): {tts_err}")

    return ChatTurnResponse(
        session_id=session_id,
        agent_text=agent_text,
        next_state=next_state,
        current_question=current_question,
        slots_extracted=slots_extracted or None,
        table_markdown=table_markdown,
        audio_b64=audio_b64,
    )


@router.delete("/reset/{session_id}")
async def reset_questionnaire(session_id: str):
    """Reset the questionnaire state for a session (useful for testing)."""
    _QUESTIONNAIRE_STATE.pop(session_id, None)
    return {"message": f"Questionnaire state reset for session {session_id}"}


# ── Internal helper ───────────────────────────────────────────────────────────

def _persist_turn(
    db: AsyncSession,
    session_id: str,
    turn_id: str,
    user_text: str,
    agent_text: str,
):
    """Add a ConversationTurn row (chat mode, no audio)."""
    db.add(ConversationTurn(
        turn_id=turn_id,
        session_id=session_id,
        turn_number=0,          # chat turns don't use the voice turn counter
        user_text=user_text,
        agent_text=agent_text,
        action_taken="CHAT_QUESTIONNAIRE",
        intent_detected=None,
        slots_extracted=None,
        was_interrupted=False,
    ))
