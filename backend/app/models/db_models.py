"""
Jan Vaani — SQLAlchemy ORM Models
All 7 SQL tables as defined in the project spec.
Note: eligibility decisions are made by the deterministic engine,
never by the LLM — these tables are the ground truth for that engine.
"""
import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy import (
    String, Integer, Float, Text, DateTime, ForeignKey,
    Enum as SAEnum, JSON, UniqueConstraint, Boolean,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.database import Base


def _uuid() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
    return datetime.utcnow()


# ─────────────────────────────────────────────────────────────
# 1. schemes
# ─────────────────────────────────────────────────────────────
class Scheme(Base):
    __tablename__ = "schemes"

    scheme_id: Mapped[str] = mapped_column(String(64), primary_key=True, default=_uuid)
    name_en: Mapped[str] = mapped_column(String(256), nullable=False)
    name_hi: Mapped[str] = mapped_column(String(256), nullable=False)
    # JSON list of informal aliases (spoken names, abbreviations, etc.)
    aliases: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON array string
    category: Mapped[str] = mapped_column(String(64), nullable=False)
    description_en: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    description_hi: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    benefits_en: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    benefits_hi: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    documents_required: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON list
    official_url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)

    rules: Mapped[list["SchemeEligibilityRule"]] = relationship(
        "SchemeEligibilityRule", back_populates="scheme", cascade="all, delete-orphan"
    )
    required_slots: Mapped[list["SchemeRequiredSlot"]] = relationship(
        "SchemeRequiredSlot", back_populates="scheme", cascade="all, delete-orphan"
    )


# ─────────────────────────────────────────────────────────────
# 2. scheme_eligibility_rules
# ─────────────────────────────────────────────────────────────
class SchemeEligibilityRule(Base):
    __tablename__ = "scheme_eligibility_rules"

    rule_id: Mapped[str] = mapped_column(String(64), primary_key=True, default=_uuid)
    scheme_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("schemes.scheme_id", ondelete="CASCADE"), nullable=False
    )
    field_name: Mapped[str] = mapped_column(String(64), nullable=False)
    # Operators: ==, !=, <, <=, >, >=, in, not_in
    operator: Mapped[str] = mapped_column(String(16), nullable=False)
    value: Mapped[str] = mapped_column(String(256), nullable=False)     # stored as string; cast by engine
    value_type: Mapped[str] = mapped_column(String(16), nullable=False)  # string | number | boolean | list
    description: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)

    scheme: Mapped["Scheme"] = relationship("Scheme", back_populates="rules")


# ─────────────────────────────────────────────────────────────
# 3. scheme_required_slots
# ─────────────────────────────────────────────────────────────
class SchemeRequiredSlot(Base):
    __tablename__ = "scheme_required_slots"

    slot_id: Mapped[str] = mapped_column(String(64), primary_key=True, default=_uuid)
    scheme_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("schemes.scheme_id", ondelete="CASCADE"), nullable=False
    )
    slot_name: Mapped[str] = mapped_column(String(64), nullable=False)
    slot_type: Mapped[str] = mapped_column(String(16), nullable=False)  # string | number | boolean | list
    question_text_en: Mapped[str] = mapped_column(Text, nullable=False)
    question_text_hi: Mapped[str] = mapped_column(Text, nullable=False)
    priority: Mapped[int] = mapped_column(Integer, default=100)         # lower = ask first

    scheme: Mapped["Scheme"] = relationship("Scheme", back_populates="required_slots")

    __table_args__ = (
        UniqueConstraint("scheme_id", "slot_name", name="uq_scheme_slot"),
    )


# ─────────────────────────────────────────────────────────────
# 4. sessions
# ─────────────────────────────────────────────────────────────
class Session(Base):
    __tablename__ = "sessions"

    session_id: Mapped[str] = mapped_column(String(64), primary_key=True, default=_uuid)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_now, onupdate=_now)
    status: Mapped[str] = mapped_column(String(32), default="active")   # active | completed | handed_off
    language: Mapped[str] = mapped_column(String(8), default="hi")       # hi | en
    current_scheme_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    current_state: Mapped[str] = mapped_column(String(64), default="IDLE")

    profile_slots: Mapped[list["UserProfileSlot"]] = relationship(
        "UserProfileSlot", back_populates="session", cascade="all, delete-orphan"
    )
    turns: Mapped[list["ConversationTurn"]] = relationship(
        "ConversationTurn", back_populates="session", cascade="all, delete-orphan"
    )
    handoffs: Mapped[list["HandoffRequest"]] = relationship(
        "HandoffRequest", back_populates="session", cascade="all, delete-orphan"
    )


# ─────────────────────────────────────────────────────────────
# 5. user_profile_slots
# PK on (session_id, slot_name) → corrections cleanly overwrite
# ─────────────────────────────────────────────────────────────
class UserProfileSlot(Base):
    __tablename__ = "user_profile_slots"

    session_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("sessions.session_id", ondelete="CASCADE"), primary_key=True
    )
    slot_name: Mapped[str] = mapped_column(String(64), primary_key=True)
    value: Mapped[str] = mapped_column(Text, nullable=False)             # always stored as string; cast at read
    confidence: Mapped[float] = mapped_column(Float, default=1.0)
    source_turn_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_now, onupdate=_now)

    session: Mapped["Session"] = relationship("Session", back_populates="profile_slots")


# ─────────────────────────────────────────────────────────────
# 6. conversation_turns
# ─────────────────────────────────────────────────────────────
class ConversationTurn(Base):
    __tablename__ = "conversation_turns"

    turn_id: Mapped[str] = mapped_column(String(64), primary_key=True, default=_uuid)
    session_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("sessions.session_id", ondelete="CASCADE"), nullable=False
    )
    turn_number: Mapped[int] = mapped_column(Integer, nullable=False)
    user_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    agent_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    action_taken: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    intent_detected: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    slots_extracted: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON
    was_interrupted: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)

    session: Mapped["Session"] = relationship("Session", back_populates="turns")


# ─────────────────────────────────────────────────────────────
# 7. handoff_requests
# ─────────────────────────────────────────────────────────────
class HandoffRequest(Base):
    __tablename__ = "handoff_requests"

    handoff_id: Mapped[str] = mapped_column(String(64), primary_key=True, default=_uuid)
    session_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("sessions.session_id", ondelete="CASCADE"), nullable=False
    )
    reason: Mapped[str] = mapped_column(String(64), nullable=False)  # low_confidence | user_request | borderline
    summary_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON blob of profile + result
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)

    session: Mapped["Session"] = relationship("Session", back_populates="handoffs")
