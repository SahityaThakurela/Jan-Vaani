"""
Jan Vaani — Pydantic Schemas (API I/O validation)
"""
from __future__ import annotations
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from datetime import datetime


# ─────────────────────────────────────────────────────────────
# Session
# ─────────────────────────────────────────────────────────────
class SessionCreate(BaseModel):
    language: str = Field(default="hi", pattern="^(hi|en)$")


class SessionResponse(BaseModel):
    session_id: str
    language: str
    status: str
    current_state: str
    created_at: datetime

    class Config:
        from_attributes = True


# ─────────────────────────────────────────────────────────────
# Scheme
# ─────────────────────────────────────────────────────────────
class SchemeOut(BaseModel):
    scheme_id: str
    name_en: str
    name_hi: str
    category: str
    description_en: Optional[str] = None
    description_hi: Optional[str] = None
    benefits_en: Optional[str] = None
    benefits_hi: Optional[str] = None
    documents_required: Optional[str] = None
    official_url: Optional[str] = None

    class Config:
        from_attributes = True


# ─────────────────────────────────────────────────────────────
# Voice Pipeline
# ─────────────────────────────────────────────────────────────
class VoiceTurnResponse(BaseModel):
    """Response for POST /voice/turn — the main pipeline endpoint."""
    session_id: str
    turn_id: str
    user_transcript: str
    agent_text: str
    audio_b64: str                          # base64-encoded MP3 from Rime
    next_state: str
    action_taken: str
    intent_detected: Optional[str] = None
    slots_extracted: Optional[Dict[str, Any]] = None
    eligibility_result: Optional["EligibilityResult"] = None
    handoff_triggered: bool = False
    cross_scheme_matches: Optional[List["CrossSchemeMatch"]] = None


class InterruptRequest(BaseModel):
    """Sent by the frontend 'Tap to Interrupt' button."""
    session_id: str


class InterruptResponse(BaseModel):
    session_id: str
    message: str
    new_state: str


# ─────────────────────────────────────────────────────────────
# Eligibility
# ─────────────────────────────────────────────────────────────
class EligibilityCheckRequest(BaseModel):
    session_id: str
    scheme_id: str
    profile: Dict[str, Any]


class EligibilityResult(BaseModel):
    scheme_id: str
    scheme_name: str
    eligible: bool
    matched_rules: int
    total_rules: int
    failed_rules: List[Dict[str, str]] = []
    missing_slots: List[str] = []
    explanation: str


class CrossSchemeMatch(BaseModel):
    scheme_id: str
    scheme_name: str
    eligible: bool
    matched_rules: int
    total_rules: int


class EligibilityCheckResponse(BaseModel):
    session_id: str
    target_result: EligibilityResult
    cross_matches: List[CrossSchemeMatch] = []


# ─────────────────────────────────────────────────────────────
# Handoff
# ─────────────────────────────────────────────────────────────
class HandoffTriggerRequest(BaseModel):
    session_id: str
    reason: str = Field(default="user_request", pattern="^(low_confidence|user_request|borderline)$")


class HandoffSummary(BaseModel):
    handoff_id: str
    session_id: str
    reason: str
    language: str
    profile: Dict[str, Any]
    target_scheme: Optional[str] = None
    eligibility_result: Optional[EligibilityResult] = None
    partial_transcript: List[Dict[str, str]] = []
    created_at: datetime

    class Config:
        from_attributes = True


# ─────────────────────────────────────────────────────────────
# User Profile Slot
# ─────────────────────────────────────────────────────────────
class ProfileSlotOut(BaseModel):
    slot_name: str
    value: str
    confidence: float
    updated_at: datetime

    class Config:
        from_attributes = True


# ─────────────────────────────────────────────────────────────
# Conversation Turn
# ─────────────────────────────────────────────────────────────
class TurnOut(BaseModel):
    turn_id: str
    turn_number: int
    user_text: Optional[str]
    agent_text: Optional[str]
    action_taken: Optional[str]
    intent_detected: Optional[str]
    was_interrupted: bool
    created_at: datetime

    class Config:
        from_attributes = True


# ─────────────────────────────────────────────────────────────
# History / Session Detail
# ─────────────────────────────────────────────────────────────
class SessionDetailResponse(BaseModel):
    session: SessionResponse
    profile: List[ProfileSlotOut]
    turns: List[TurnOut]
    handoffs: List[Dict[str, Any]]


# ─────────────────────────────────────────────────────────────
# Auth
# ─────────────────────────────────────────────────────────────
class UserRegister(BaseModel):
    email: str = Field(..., description="User email address")
    password: str = Field(..., min_length=6, description="Password (min 6 chars)")
    full_name: Optional[str] = Field(default=None)


class UserLogin(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: str
    email: str
    full_name: Optional[str] = None


class UserOut(BaseModel):
    user_id: str
    email: str
    full_name: Optional[str] = None
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


# ─────────────────────────────────────────────────────────────
# Text Chat (Questionnaire)
# ─────────────────────────────────────────────────────────────
class ChatTurnRequest(BaseModel):
    session_id: str
    message: str = Field(..., min_length=1, max_length=2000)
    language: str = Field(default="hi", pattern="^(hi|en)$")
    with_audio: bool = Field(default=False, description="If True, synthesize TTS and return audio_b64")


class ChatTurnResponse(BaseModel):
    session_id: str
    agent_text: str
    next_state: str                         # GREETING | COLLECTING | COMPLETE
    current_question: Optional[int] = None  # 1-based index of current Q, None when done
    slots_extracted: Optional[Dict[str, Any]] = None
    table_markdown: Optional[str] = None    # Populated only when state == COMPLETE
    audio_b64: Optional[str] = None         # Base64 MP3 audio, populated when with_audio=True
