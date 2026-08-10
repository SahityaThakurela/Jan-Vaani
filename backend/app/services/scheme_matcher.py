"""
Jan Vaani — Cross-Scheme Matcher
Runs the deterministic eligibility engine across ALL schemes
using the profile data collected so far, and returns a ranked
list of other schemes the user qualifies for.
"""
from typing import Any, Dict, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.db_models import Scheme, SchemeEligibilityRule, SchemeRequiredSlot
from app.services.eligibility_engine import evaluate_eligibility, EligibilityDecision
from app.utils.logger import get_logger

logger = get_logger(__name__)


async def run_cross_scheme_match(
    profile: Dict[str, Any],
    db: AsyncSession,
    exclude_scheme_id: str | None = None,
) -> List[EligibilityDecision]:
    """
    Check the user's filled profile against every scheme in the DB.
    Returns a ranked list (eligible first) of EligibilityDecision objects.

    Args:
        profile: Dict of {slot_name: typed_value} — all filled slots for this session.
        db: Async SQLAlchemy session.
        exclude_scheme_id: Scheme to skip (usually the primary target scheme).
    """
    # Fetch all schemes
    result = await db.execute(select(Scheme))
    schemes = result.scalars().all()

    decisions: List[EligibilityDecision] = []

    for scheme in schemes:
        if exclude_scheme_id and scheme.scheme_id == exclude_scheme_id:
            continue

        # Fetch rules for this scheme
        rules_result = await db.execute(
            select(SchemeEligibilityRule).where(
                SchemeEligibilityRule.scheme_id == scheme.scheme_id
            )
        )
        rules = [
            {
                "field_name": r.field_name,
                "operator": r.operator,
                "value": r.value,
                "value_type": r.value_type,
            }
            for r in rules_result.scalars().all()
        ]

        # Fetch required slots
        slots_result = await db.execute(
            select(SchemeRequiredSlot).where(
                SchemeRequiredSlot.scheme_id == scheme.scheme_id
            ).order_by(SchemeRequiredSlot.priority)
        )
        required_slots = [s.slot_name for s in slots_result.scalars().all()]

        decision = evaluate_eligibility(
            scheme_id=scheme.scheme_id,
            scheme_name=scheme.name_en,
            rules=rules,
            required_slots=required_slots,
            profile=profile,
        )
        decisions.append(decision)
        logger.debug(
            f"Cross-match {scheme.scheme_id}: eligible={decision.eligible} "
            f"({decision.matched_rules}/{decision.total_rules} rules)"
        )

    # Sort: eligible first, then by number of rules matched (desc)
    decisions.sort(key=lambda d: (-int(d.eligible), -d.matched_rules))
    return decisions
