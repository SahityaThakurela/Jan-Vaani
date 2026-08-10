"""
Jan Vaani — LLM Service (Google Gemini)

Responsibilities (ONLY fuzzy/language tasks — never eligibility decisions):
  1. Intent classification: SEARCH_SCHEMES | SCHEME_DETAIL | ELIGIBILITY_CHECK | CORRECTION | HANDOFF_REQUEST
  2. Slot extraction: convert free-speech answer → structured {slot_name: value}
  3. Reply composition: generate short, spoken-natural agent replies
  4. Correction detection: identify if user is correcting a previously given value
"""
import json
from typing import Any, Dict, List, Optional
import google.generativeai as genai
from app.config import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)

# Supported intents
INTENT_SEARCH = "SEARCH_SCHEMES"
INTENT_DETAIL = "SCHEME_DETAIL"
INTENT_ELIGIBILITY = "ELIGIBILITY_CHECK"
INTENT_CORRECTION = "CORRECTION"
INTENT_HANDOFF = "HANDOFF_REQUEST"
INTENT_UNCLEAR = "UNCLEAR"

VALID_INTENTS = {INTENT_SEARCH, INTENT_DETAIL, INTENT_ELIGIBILITY, INTENT_CORRECTION, INTENT_HANDOFF, INTENT_UNCLEAR}


def _get_model(system_instruction: str = "") -> genai.GenerativeModel:
    genai.configure(api_key=settings.gemini_api_key)
    return genai.GenerativeModel(
        model_name=settings.gemini_model,
        system_instruction=system_instruction or (
            "You are Jan Vaani, a voice assistant that helps rural Indian users navigate government welfare schemes. "
            "Always respond in the same language the user spoke (Hindi or English). "
            "Be concise, warm, and use simple language. Avoid jargon. "
            "Never make up eligibility decisions — that is done by a separate rules engine."
        ),
        generation_config=genai.GenerationConfig(
            temperature=0.2,
            max_output_tokens=512,
        ),
    )


async def classify_intent(
    user_text: str,
    language: str = "hi",
    conversation_context: List[Dict[str, str]] | None = None,
) -> Dict[str, Any]:
    """
    Classify the user's intent from their spoken text.

    Returns:
        {
            "intent": "SEARCH_SCHEMES" | "SCHEME_DETAIL" | "ELIGIBILITY_CHECK" | "CORRECTION" | "HANDOFF_REQUEST" | "UNCLEAR",
            "scheme_hint": "PM-KISAN" | null,   # if user mentioned a specific scheme
            "confidence": 0.0–1.0,
            "correction_field": null | "field_name",  # if intent is CORRECTION
            "correction_value": null | "new_value",
        }
    """
    if not settings.gemini_api_key:
        return {"intent": INTENT_UNCLEAR, "scheme_hint": None, "confidence": 0.5}

    context_str = ""
    if conversation_context:
        context_str = "\nRecent conversation:\n" + "\n".join(
            f"{'User' if t['role'] == 'user' else 'Agent'}: {t['text']}"
            for t in conversation_context[-4:]
        )

    prompt = f"""Classify the user's intent from their message. Return ONLY a valid JSON object.

User message: "{user_text}"
Language: {language}
{context_str}

Possible intents:
- SEARCH_SCHEMES: user wants to find/browse government schemes
- SCHEME_DETAIL: user wants info about a specific scheme
- ELIGIBILITY_CHECK: user wants to check if they qualify for a scheme
- CORRECTION: user is correcting a previously given answer (e.g., "no, I meant 3 acres, not 2")
- HANDOFF_REQUEST: user explicitly asks to talk to a human
- UNCLEAR: cannot determine intent

Respond with ONLY this JSON (no markdown, no explanation):
{{"intent": "...", "scheme_hint": null_or_scheme_name, "confidence": 0.0_to_1.0, "correction_field": null, "correction_value": null}}"""

    try:
        model = _get_model()
        response = await model.generate_content_async(prompt)
        text = response.text.strip()
        # Strip markdown code fences if present
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        result = json.loads(text.strip())
        # Validate intent
        if result.get("intent") not in VALID_INTENTS:
            result["intent"] = INTENT_UNCLEAR
        return result
    except Exception as e:
        logger.error(f"Intent classification failed: {e}")
        return {"intent": INTENT_UNCLEAR, "scheme_hint": None, "confidence": 0.0}


async def extract_slots(
    user_text: str,
    slots_to_fill: List[Dict[str, str]],
    language: str = "hi",
) -> Dict[str, Any]:
    """
    Extract structured slot values from the user's free-speech answer.

    Args:
        user_text: The user's spoken text.
        slots_to_fill: List of {slot_name, slot_type, question_text_en/hi} — which slots we asked about.
        language: "hi" or "en"

    Returns:
        {slot_name: extracted_value, ...} — may be partial (only confidently extracted slots)
    """
    if not settings.gemini_api_key or not slots_to_fill:
        return {}

    slot_descriptions = "\n".join(
        f"- {s['slot_name']} ({s['slot_type']}): {s.get('question_text_en', '')}"
        for s in slots_to_fill
    )

    prompt = f"""Extract structured values from the user's spoken reply.

User said: "{user_text}"
Language: {language}

Slots to extract:
{slot_descriptions}

Rules:
- Extract values ONLY if you are confident. Skip uncertain slots.
- For boolean slots: return true or false (Python bool as string: "true"/"false")
- For number slots: return numeric value as string (e.g., "2.5" for 2.5 acres)
- For string slots: return the normalized English value where possible
- Convert Hinglish/Hindi numbers/words to values (e.g., "do acre" → 2, "haan" → true, "nahin" → false)

Respond with ONLY a JSON object (no markdown):
{{"slot_name": "extracted_value", ...}}
If nothing can be extracted, return {{}}"""

    try:
        model = _get_model("You are a structured data extractor. Extract slot values from spoken replies.")
        response = await model.generate_content_async(prompt)
        text = response.text.strip()
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        result = json.loads(text.strip())
        logger.debug(f"Slots extracted: {result}")
        return result
    except Exception as e:
        logger.error(f"Slot extraction failed: {e}")
        return {}


async def compose_reply(
    situation: str,
    context: Dict[str, Any],
    language: str = "hi",
) -> str:
    """
    Compose a short, spoken-natural agent reply for a given situation.

    situation: one of:
      "welcome" | "ask_slot" | "clarify" | "search_result" | "scheme_detail" |
      "eligibility_result" | "cross_match" | "handoff" | "correction_ack" | "error"

    Rime Coda note: No SSML supported. Shape delivery via wording and punctuation only.
    """
    if not settings.gemini_api_key:
        # Fallback stub responses
        fallbacks = {
            "welcome": "Namaste! Main Jan Vaani hun. Aap kaunsi sarkari yojana ke baare mein jaanna chahte hain?",
            "ask_slot": context.get("question", "Kripya mujhe aur jaankari dijiye."),
            "eligibility_result": context.get("explanation", "Eligibility check complete."),
            "error": "Kuch gadbad ho gayi. Dobara poochhen.",
        }
        return fallbacks.get(situation, context.get("question", "Haan, boliye."))

    system = (
        "You are Jan Vaani, a warm and helpful voice assistant for rural Indian users. "
        "Always respond concisely (1-3 sentences). Use simple, spoken language. "
        "No bullet points, no markdown, no long paragraphs — this is spoken audio. "
        "Shape delivery via punctuation and wording only (no SSML). "
        f"Respond in {'Hindi' if language == 'hi' else 'English'}."
    )

    context_str = json.dumps(context, ensure_ascii=False, indent=2)
    prompt = f"""Generate a natural spoken response for this situation.

Situation: {situation}
Context: {context_str}

Requirements:
- Maximum 3 sentences
- Natural spoken Hindi or English (not written style)
- End with a question only if you need more info from the user
- Do NOT include markdown, lists, or headers"""

    try:
        model = _get_model(system)
        response = await model.generate_content_async(prompt)
        return response.text.strip()
    except Exception as e:
        logger.error(f"Reply composition failed: {e}")
        return "Kuch gadbad ho gayi. Dobara poochhen."


async def resolve_scheme_name(
    spoken_name: str,
    available_schemes: List[Dict[str, str]],
    language: str = "hi",
) -> Optional[str]:
    """
    Resolve a spoken/informal scheme name to a scheme_id.
    e.g., "kisan wali yojana" → "PM-KISAN-001"
    """
    if not settings.gemini_api_key or not available_schemes:
        return None

    schemes_list = "\n".join(
        f"- {s['scheme_id']}: {s['name_en']} / {s['name_hi']} (aliases: {s.get('aliases', '')})"
        for s in available_schemes
    )

    prompt = f"""The user mentioned a government scheme. Match it to the correct scheme_id.

User said: "{spoken_name}"

Available schemes:
{schemes_list}

Return ONLY the scheme_id (e.g., "PM-KISAN-001") or "UNKNOWN" if no match."""

    try:
        model = _get_model("You are a scheme name resolver. Return only the scheme_id.")
        response = await model.generate_content_async(prompt)
        result = response.text.strip().strip('"')
        if result == "UNKNOWN":
            return None
        return result
    except Exception as e:
        logger.error(f"Scheme name resolution failed: {e}")
        return None
