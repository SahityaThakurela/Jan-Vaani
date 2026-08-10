"""
Jan Vaani — Eligibility Routes
POST /eligibility/check  → direct eligibility check (for testing/debug)
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.database import get_db
from app.models.db_models import Scheme, SchemeEligibilityRule, SchemeRequiredSlot
from app.models.schemas import EligibilityCheckRequest, EligibilityCheckResponse, EligibilityResult, CrossSchemeMatch
from app.services.eligibility_engine import evaluate_eligibility
from app.services.scheme_matcher import run_cross_scheme_match
from app.utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter()


@router.post("/check", response_model=EligibilityCheckResponse)
async def check_eligibility(
    payload: EligibilityCheckRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Directly check eligibility for a scheme + profile.
    Used for testing the deterministic engine and for the frontend debug panel.
    """
    # Fetch scheme
    scheme_result = await db.execute(
        select(Scheme).where(Scheme.scheme_id == payload.scheme_id)
    )
    scheme = scheme_result.scalar_one_or_none()
    if not scheme:
        raise HTTPException(status_code=404, detail=f"Scheme '{payload.scheme_id}' not found.")

    # Fetch rules
    rules_result = await db.execute(
        select(SchemeEligibilityRule).where(SchemeEligibilityRule.scheme_id == payload.scheme_id)
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
        select(SchemeRequiredSlot)
        .where(SchemeRequiredSlot.scheme_id == payload.scheme_id)
        .order_by(SchemeRequiredSlot.priority)
    )
    required_slots = [s.slot_name for s in slots_result.scalars().all()]

    # Run eligibility engine
    decision = evaluate_eligibility(
        scheme_id=payload.scheme_id,
        scheme_name=scheme.name_en,
        rules=rules,
        required_slots=required_slots,
        profile=payload.profile,
    )

    target_result = EligibilityResult(
        scheme_id=decision.scheme_id,
        scheme_name=decision.scheme_name,
        eligible=decision.eligible,
        matched_rules=decision.matched_rules,
        total_rules=decision.total_rules,
        failed_rules=[{"field": r.field_name, "reason": r.reason} for r in decision.failed_rules],
        missing_slots=decision.missing_slots,
        explanation=decision.explanation,
    )

    # Cross-scheme matching
    cross_decisions = await run_cross_scheme_match(
        profile=payload.profile, db=db, exclude_scheme_id=payload.scheme_id
    )
    cross_matches = [
        CrossSchemeMatch(
            scheme_id=d.scheme_id,
            scheme_name=d.scheme_name,
            eligible=d.eligible,
            matched_rules=d.matched_rules,
            total_rules=d.total_rules,
        )
        for d in cross_decisions[:5]
    ]

    return EligibilityCheckResponse(
        session_id=payload.session_id,
        target_result=target_result,
        cross_matches=cross_matches,
    )
