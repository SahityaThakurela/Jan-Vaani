"""
Jan Vaani — LLM Service (OpenRouter Integration)
"""
import os
import json
from typing import Any, Dict, List, Optional
from openai import AsyncOpenAI
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

# Initialize OpenRouter Client
from dotenv import load_dotenv
load_dotenv() # This forces Python to read your .env file!
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

def _get_client() -> AsyncOpenAI:
    return AsyncOpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=OPENROUTER_API_KEY,
    )

# You can swap this to "google/gemini-2.5-pro", "meta-llama/llama-3-70b-instruct", etc.
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "google/gemini-2.5-flash")

async def classify_intent(
    user_text: str,
    language: str = "hi",
    conversation_context: Optional[List[Dict[str, str]]] = None,
) -> Dict[str, Any]:
    
    if not OPENROUTER_API_KEY:
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
- CORRECTION: user is correcting a previously given answer
- HANDOFF_REQUEST: user explicitly asks to talk to a human
- UNCLEAR: cannot determine intent

Respond with ONLY this JSON (no markdown, no explanation):
{{"intent": "...", "scheme_hint": null_or_scheme_name, "confidence": 0.0_to_1.0, "correction_field": null, "correction_value": null}}"""

    try:
        client = _get_client()
        response = await client.chat.completions.create(
            model=OPENROUTER_MODEL,
            messages=[
                {"role": "system", "content": "You are a JSON-only API. Output raw JSON without Markdown formatting."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,
            max_tokens=300,
        )
        text = response.choices[0].message.content.strip()
        
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
                
        result = json.loads(text.strip())
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
    
    if not OPENROUTER_API_KEY or not slots_to_fill:
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
- For boolean slots: return true or false
- For number slots: return numeric value as string (e.g., "2.5" for 2.5 acres)
- For string slots: return the normalized English value where possible

Respond with ONLY a JSON object (no markdown):
{{"slot_name": "extracted_value", ...}}
If nothing can be extracted, return {{}}"""

    try:
        client = _get_client()
        response = await client.chat.completions.create(
            model=OPENROUTER_MODEL,
            messages=[
                {"role": "system", "content": "You are a JSON-only API. Output raw JSON without Markdown formatting."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,
            max_tokens=300,
        )
        text = response.choices[0].message.content.strip()
        
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
                
        result = json.loads(text.strip())
        return result
    except Exception as e:
        logger.error(f"Slot extraction failed: {e}")
        return {}

async def compose_reply(
    situation: str,
    context: Dict[str, Any],
    language: str = "hi",
    conversation_history: Optional[List[Dict[str, str]]] = None,
) -> str:
    
    if not OPENROUTER_API_KEY:
        fallbacks = {
            "welcome": "Namaste! Main Jan Vaani hun. Aap kaunsi sarkari yojana ke baare mein jaanna chahte hain?",
            "error": "Kuch gadbad ho gayi. Dobara poochhen.",
        }
        return fallbacks.get(situation, context.get("question", "Haan, boliye."))

    lang_name = "Hindi" if language == "hi" else "English"
    system = (
        "You are Jan Vaani, a knowledgeable and warm voice assistant helping rural Indian citizens "
        "navigate government welfare schemes (Yojanas). You have deep knowledge of Indian government "
        "schemes like PM-KISAN, Pradhan Mantri Awas Yojana (PMAY-G), Ayushman Bharat, MGNREGA, "
        "PM Fasal Bima Yojana, PM Ujjwala Yojana, and similar programs.\n\n"
        "RESPONSE RULES:\n"
        "- Always respond in a warm, clear, conversational spoken style.\n"
        "- Keep responses to 2-4 sentences maximum. This is spoken audio, not text.\n"
        "- Never use bullet points, markdown, asterisks, or numbered lists.\n"
        "- Be specific and helpful. If you know eligibility criteria, state them clearly.\n"
        "- If the user corrects you or gives new information, acknowledge it naturally and continue.\n"
        "- Maintain full context of the entire conversation above when responding.\n"
        f"- Always respond in {lang_name}."
    )

    # ── Build the full multi-turn messages list ──────────────
    messages = [{"role": "system", "content": system}]

    # Inject conversation history as real user/assistant turns
    if conversation_history:
        for turn in conversation_history:
            role = turn.get("role", "user")
            text = turn.get("text", "").strip()
            if not text:
                continue
            # Map agent → assistant for OpenAI API format
            api_role = "assistant" if role == "agent" else "user"
            messages.append({"role": api_role, "content": text})

    # Append the current situation prompt as the final user message
    context_str = json.dumps(context, ensure_ascii=False, indent=2)
    current_prompt = (
        f"Situation: {situation}\n"
        f"Context: {context_str}\n\n"
        f"Generate a natural, helpful spoken response in {lang_name}. "
        "No bullet points. No markdown. 2-4 sentences max."
    )
    messages.append({"role": "user", "content": current_prompt})

    try:
        client = _get_client()
        response = await client.chat.completions.create(
            model=OPENROUTER_MODEL,
            messages=messages,
            temperature=0.4,
            max_tokens=400,   # increased from 200 for richer, complete responses
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"Reply composition failed: {e}")
        return "Kuch gadbad ho gayi. Dobara poochhen."

async def generate_session_title(user_query: str, language: str = "hi") -> str:
    """Generates a concise 3-5 word title for the session based on the first query."""
    if not OPENROUTER_API_KEY:
        return "New Chat"

    prompt = (
        f"You are a helpful assistant. The user just started a conversation with the following query:\n"
        f"\"{user_query}\"\n\n"
        f"Generate a very concise, meaningful title for this session (3 to 5 words max). "
        f"Do not use quotes. Use the same language the user used ({language})."
    )

    try:
        client = _get_client()
        response = await client.chat.completions.create(
            model=OPENROUTER_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=20,
        )
        return response.choices[0].message.content.strip().strip('"')
    except Exception as e:
        logger.error(f"Title generation failed: {e}")
        return "New Chat"

async def resolve_scheme_name(
    spoken_name: str,
    available_schemes: List[Dict[str, str]],
    language: str = "hi",
) -> Optional[str]:
    
    if not OPENROUTER_API_KEY or not available_schemes:
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
        client = _get_client()
        response = await client.chat.completions.create(
            model=OPENROUTER_MODEL,
            messages=[
                {"role": "system", "content": "You are a scheme name resolver. Return only the scheme_id."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,
            max_tokens=50,
        )
        result = response.choices[0].message.content.strip().strip('"')
        if result == "UNKNOWN":
            return None
        return result
    except Exception as e:
        logger.error(f"Scheme name resolution failed: {e}")
        return None