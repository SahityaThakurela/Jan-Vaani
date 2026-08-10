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
) -> str:
    
    if not OPENROUTER_API_KEY:
        fallbacks = {
            "welcome": "Namaste! Main Jan Vaani hun. Aap kaunsi sarkari yojana ke baare mein jaanna chahte hain?",
            "error": "Kuch gadbad ho gayi. Dobara poochhen.",
        }
        return fallbacks.get(situation, context.get("question", "Haan, boliye."))

    system = (
        "You are Jan Vaani, a warm and helpful voice assistant for rural Indian users. "
        "Always respond concisely (1-3 sentences). Use simple, spoken language. "
        "No bullet points, no markdown, no long paragraphs — this is spoken audio. "
        f"Respond in {'Hindi' if language == 'hi' else 'English'}."
    )

    context_str = json.dumps(context, ensure_ascii=False, indent=2)
    prompt = f"""Generate a natural spoken response for this situation.

Situation: {situation}
Context: {context_str}

Requirements:
- Maximum 3 sentences
- Natural spoken style
- End with a question only if you need more info"""

    try:
        client = _get_client()
        response = await client.chat.completions.create(
            model=OPENROUTER_MODEL,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=200,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"Reply composition failed: {e}")
        return "Kuch gadbad ho gayi. Dobara poochhen."

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