"""
Jan Vaani — Session State Machine

States:
  IDLE → user opens session / taps interrupt
  INTENT_CLASSIFICATION → classifying what the user wants
  SEARCH_SCHEMES → searching Qdrant for scheme info
  SCHEME_DETAIL → retrieving and explaining a specific scheme
  ELIGIBILITY_CHECK → filling slots one at a time + running engine
  RESULT → eligibility decision delivered
  HANDOFF → transferring to human agent

Transitions are deterministic; only routing logic lives here.
LLM/engine calls happen in the voice route, not in this module.
"""
from __future__ import annotations
from enum import Enum
from typing import Any, Dict, Optional
from app.utils.logger import get_logger

logger = get_logger(__name__)


class SessionState(str, Enum):
    IDLE = "IDLE"
    INTENT_CLASSIFICATION = "INTENT_CLASSIFICATION"
    SEARCH_SCHEMES = "SEARCH_SCHEMES"
    SCHEME_DETAIL = "SCHEME_DETAIL"
    ELIGIBILITY_CHECK = "ELIGIBILITY_CHECK"
    RESULT = "RESULT"
    HANDOFF = "HANDOFF"


# Valid state transitions
TRANSITIONS: Dict[SessionState, list[SessionState]] = {
    SessionState.IDLE: [
        SessionState.INTENT_CLASSIFICATION,
    ],
    SessionState.INTENT_CLASSIFICATION: [
        SessionState.SEARCH_SCHEMES,
        SessionState.SCHEME_DETAIL,
        SessionState.ELIGIBILITY_CHECK,
        SessionState.HANDOFF,
        SessionState.IDLE,
    ],
    SessionState.SEARCH_SCHEMES: [
        SessionState.SCHEME_DETAIL,
        SessionState.ELIGIBILITY_CHECK,
        SessionState.IDLE,
        SessionState.INTENT_CLASSIFICATION,
    ],
    SessionState.SCHEME_DETAIL: [
        SessionState.ELIGIBILITY_CHECK,
        SessionState.IDLE,
        SessionState.INTENT_CLASSIFICATION,
    ],
    SessionState.ELIGIBILITY_CHECK: [
        SessionState.ELIGIBILITY_CHECK,    # loop: ask next slot
        SessionState.RESULT,
        SessionState.HANDOFF,
        SessionState.IDLE,
    ],
    SessionState.RESULT: [
        SessionState.IDLE,
        SessionState.ELIGIBILITY_CHECK,
        SessionState.SEARCH_SCHEMES,
        SessionState.HANDOFF,
    ],
    SessionState.HANDOFF: [
        SessionState.IDLE,
    ],
}


class StateMachine:
    """
    Lightweight state machine for a single session.
    Holds: current state, turn count, target scheme_id, interruption flag.
    """

    def __init__(self, session_id: str, initial_state: SessionState = SessionState.IDLE):
        self.session_id = session_id
        self.state: SessionState = initial_state
        self.turn_count: int = 0
        self.target_scheme_id: Optional[str] = None
        self.is_interrupted: bool = False
        self.consecutive_low_conf_turns: int = 0
        self._extra: Dict[str, Any] = {}  # arbitrary per-state scratch data

    def can_transition_to(self, new_state: SessionState) -> bool:
        return new_state in TRANSITIONS.get(self.state, [])

    def transition(self, new_state: SessionState, **kwargs) -> bool:
        """
        Attempt a state transition. Returns True on success.
        kwargs are stored in _extra for the next turn to read.
        """
        if not self.can_transition_to(new_state):
            logger.warning(
                f"[{self.session_id}] Invalid transition: {self.state} → {new_state}"
            )
            return False
        logger.info(f"[{self.session_id}] State: {self.state} → {new_state}")
        self.state = new_state
        self._extra.update(kwargs)
        return True

    def interrupt(self):
        """
        Handle 'Tap to Interrupt'.
        Resets intent/turn state but preserves all filled slots.
        Agent returns to IDLE, ready for a fresh request.
        """
        logger.info(f"[{self.session_id}] INTERRUPT triggered (state was {self.state})")
        self.state = SessionState.IDLE
        self.is_interrupted = True
        self.target_scheme_id = None
        self.consecutive_low_conf_turns = 0
        self._extra = {}

    def increment_turn(self):
        self.turn_count += 1
        self.is_interrupted = False  # clear flag after turn

    def mark_low_confidence(self):
        self.consecutive_low_conf_turns += 1

    def reset_low_confidence(self):
        self.consecutive_low_conf_turns = 0

    def should_trigger_handoff(self) -> bool:
        """Trigger handoff after 3 consecutive low-confidence turns."""
        return self.consecutive_low_conf_turns >= 3

    def set_extra(self, key: str, value: Any):
        self._extra[key] = value

    def get_extra(self, key: str, default: Any = None) -> Any:
        return self._extra.get(key, default)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "state": self.state.value,
            "turn_count": self.turn_count,
            "target_scheme_id": self.target_scheme_id,
            "is_interrupted": self.is_interrupted,
            "consecutive_low_conf_turns": self.consecutive_low_conf_turns,
        }


# In-memory registry: session_id → StateMachine
_state_machines: Dict[str, StateMachine] = {}


def get_state_machine(session_id: str, initial_state: str = "IDLE") -> StateMachine:
    """Get or create a StateMachine for a session."""
    if session_id not in _state_machines:
        _state_machines[session_id] = StateMachine(
            session_id=session_id,
            initial_state=SessionState(initial_state),
        )
    return _state_machines[session_id]


def remove_state_machine(session_id: str):
    """Remove state machine when session ends."""
    _state_machines.pop(session_id, None)
