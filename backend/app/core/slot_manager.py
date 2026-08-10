"""
Jan Vaani — Session Slot Manager

Manages in-memory slot state per session, backed by SQLite for persistence.
Handles:
  - Slot filling (upsert → corrections overwrite cleanly)
  - Getting unfilled required slots
  - Loading/saving profile from DB
  - Tracking confidence per slot
"""
from __future__ import annotations
import json
from typing import Any, Dict, List, Optional
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from app.models.db_models import UserProfileSlot, SchemeRequiredSlot
from app.utils.logger import get_logger

logger = get_logger(__name__)


class SlotManager:
    """
    Per-session slot state manager.
    In-memory dict is the fast-path; DB is the persistent store.
    """

    def __init__(self, session_id: str):
        self.session_id = session_id
        self._slots: Dict[str, Dict[str, Any]] = {}  # slot_name → {value, confidence, updated_at}

    # ── In-memory operations ──────────────────────────────────
    def fill_slot(
        self,
        slot_name: str,
        value: Any,
        confidence: float = 1.0,
        source_turn_id: Optional[str] = None,
    ):
        """Fill or overwrite a slot (correction semantics)."""
        was_correction = slot_name in self._slots
        self._slots[slot_name] = {
            "value": value,
            "confidence": confidence,
            "source_turn_id": source_turn_id,
            "updated_at": datetime.utcnow().isoformat(),
        }
        if was_correction:
            logger.info(f"[{self.session_id}] CORRECTION: slot '{slot_name}' overwritten → {value}")
        else:
            logger.debug(f"[{self.session_id}] Slot filled: '{slot_name}' = {value} (conf={confidence:.2f})")

    def fill_slots_from_dict(
        self,
        extracted: Dict[str, Any],
        confidence: float = 0.9,
        source_turn_id: Optional[str] = None,
    ):
        """Bulk fill slots from LLM extraction result."""
        for slot_name, value in extracted.items():
            if value is not None and value != "":
                self.fill_slot(slot_name, value, confidence, source_turn_id)

    def get_slot(self, slot_name: str) -> Optional[Any]:
        """Get a slot value, or None if not filled."""
        entry = self._slots.get(slot_name)
        return entry["value"] if entry else None

    def get_profile(self) -> Dict[str, Any]:
        """Get all filled slots as a flat {slot_name: value} dict."""
        return {k: v["value"] for k, v in self._slots.items()}

    def get_missing_slots(self, required_slots: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Return the list of required slots not yet filled, ordered by priority.

        Args:
            required_slots: List of slot dicts from DB (slot_name, priority, question_text_en/hi, ...)
        """
        missing = [s for s in required_slots if s["slot_name"] not in self._slots]
        missing.sort(key=lambda s: s.get("priority", 100))
        return missing

    def has_low_confidence_slot(self, threshold: float = 0.5) -> Optional[str]:
        """Return the name of the first slot with confidence below threshold, or None."""
        for name, data in self._slots.items():
            if data["confidence"] < threshold:
                return name
        return None

    def to_dict(self) -> Dict[str, Any]:
        return dict(self._slots)

    # ── DB persistence ────────────────────────────────────────
    async def load_from_db(self, db: AsyncSession):
        """Load slot state from DB into memory (call on session resume)."""
        result = await db.execute(
            select(UserProfileSlot).where(UserProfileSlot.session_id == self.session_id)
        )
        rows = result.scalars().all()
        for row in rows:
            self._slots[row.slot_name] = {
                "value": row.value,
                "confidence": row.confidence,
                "source_turn_id": row.source_turn_id,
                "updated_at": row.updated_at.isoformat() if row.updated_at else None,
            }
        logger.debug(f"[{self.session_id}] Loaded {len(rows)} slots from DB.")

    async def persist_to_db(self, db: AsyncSession):
        """Upsert all in-memory slots to DB (called after each turn)."""
        for slot_name, data in self._slots.items():
            # SQLite upsert: insert or replace on (session_id, slot_name) PK
            stmt = sqlite_insert(UserProfileSlot).values(
                session_id=self.session_id,
                slot_name=slot_name,
                value=str(data["value"]),
                confidence=data["confidence"],
                source_turn_id=data.get("source_turn_id"),
                updated_at=datetime.utcnow(),
            ).on_conflict_do_update(
                index_elements=["session_id", "slot_name"],
                set_={
                    "value": str(data["value"]),
                    "confidence": data["confidence"],
                    "source_turn_id": data.get("source_turn_id"),
                    "updated_at": datetime.utcnow(),
                },
            )
            await db.execute(stmt)
        await db.commit()
        logger.debug(f"[{self.session_id}] Persisted {len(self._slots)} slots to DB.")


# In-memory registry of active SlotManagers (session_id → SlotManager)
_slot_managers: Dict[str, SlotManager] = {}


def get_slot_manager(session_id: str) -> SlotManager:
    """Get or create a SlotManager for a session."""
    if session_id not in _slot_managers:
        _slot_managers[session_id] = SlotManager(session_id)
    return _slot_managers[session_id]


def remove_slot_manager(session_id: str):
    """Remove slot manager when session ends."""
    _slot_managers.pop(session_id, None)
