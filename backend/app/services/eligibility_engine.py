"""
Jan Vaani — Deterministic Eligibility Engine

IMPORTANT: This module contains ZERO AI / LLM calls.
It evaluates structured rules (stored in scheme_eligibility_rules table)
against a structured profile dict. Every decision is explicit, testable,
and fully auditable — a requirement for a high-trust government benefit workflow.

Supported operators: ==, !=, <, <=, >, >=, in, not_in
Supported value types: string, number, boolean, list
"""
import json
import ast
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple
from app.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class RuleResult:
    """Result of evaluating a single eligibility rule."""
    field_name: str
    operator: str
    expected_value: str
    actual_value: Any
    passed: bool
    reason: str = ""


@dataclass
class EligibilityDecision:
    """Complete result of evaluating all rules for one scheme."""
    scheme_id: str
    scheme_name: str
    eligible: bool
    matched_rules: int
    total_rules: int
    failed_rules: List[RuleResult] = field(default_factory=list)
    missing_slots: List[str] = field(default_factory=list)
    explanation: str = ""


def _cast_value(raw: str, value_type: str) -> Any:
    """Cast a stored string value to its target Python type."""
    try:
        if value_type == "number":
            return float(raw)
        elif value_type == "boolean":
            return raw.strip().lower() in ("true", "1", "yes", "हाँ", "हां")
        elif value_type == "list":
            # Stored as JSON array string e.g. '["farmer", "kisan"]'
            return json.loads(raw)
        else:
            return str(raw).strip().lower()
    except Exception as e:
        logger.warning(f"Could not cast '{raw}' as {value_type}: {e}")
        return raw


def _cast_profile_value(raw: Any, value_type: str) -> Any:
    """Cast a profile value (from user input, possibly typed) to the target type."""
    if raw is None:
        return None
    if value_type == "number":
        try:
            return float(str(raw).replace(",", ""))
        except Exception:
            return None
    elif value_type == "boolean":
        if isinstance(raw, bool):
            return raw
        return str(raw).strip().lower() in ("true", "1", "yes", "हाँ", "हां")
    elif value_type == "list":
        if isinstance(raw, list):
            return [str(v).strip().lower() for v in raw]
        return [str(raw).strip().lower()]
    else:
        return str(raw).strip().lower()


def _evaluate_rule(
    field_name: str,
    operator: str,
    expected_raw: str,
    value_type: str,
    profile: Dict[str, Any],
) -> RuleResult:
    """
    Evaluate a single eligibility rule against the profile.

    Returns a RuleResult with passed=True if the rule is satisfied.
    """
    if field_name not in profile or profile[field_name] is None:
        return RuleResult(
            field_name=field_name,
            operator=operator,
            expected_value=expected_raw,
            actual_value=None,
            passed=False,
            reason=f"Missing profile slot: '{field_name}'",
        )

    expected = _cast_value(expected_raw, value_type)
    actual = _cast_profile_value(profile[field_name], value_type)

    if actual is None:
        return RuleResult(
            field_name=field_name,
            operator=operator,
            expected_value=expected_raw,
            actual_value=profile[field_name],
            passed=False,
            reason=f"Could not parse '{profile[field_name]}' as {value_type}",
        )

    try:
        if operator == "==":
            passed = actual == expected
        elif operator == "!=":
            passed = actual != expected
        elif operator == "<":
            passed = actual < expected
        elif operator == "<=":
            passed = actual <= expected
        elif operator == ">":
            passed = actual > expected
        elif operator == ">=":
            passed = actual >= expected
        elif operator == "in":
            # Check if actual value (or any element) is in the expected list
            if isinstance(expected, list):
                if isinstance(actual, list):
                    passed = any(a in expected for a in actual)
                else:
                    passed = actual in expected
            else:
                passed = actual == expected
        elif operator == "not_in":
            if isinstance(expected, list):
                if isinstance(actual, list):
                    passed = not any(a in expected for a in actual)
                else:
                    passed = actual not in expected
            else:
                passed = actual != expected
        else:
            logger.error(f"Unknown operator: {operator}")
            passed = False
    except TypeError as e:
        logger.error(f"Type error comparing {actual!r} {operator} {expected!r}: {e}")
        passed = False

    reason = "" if passed else (
        f"'{field_name}' is {actual!r}, but rule requires {operator} {expected!r}"
    )

    return RuleResult(
        field_name=field_name,
        operator=operator,
        expected_value=expected_raw,
        actual_value=actual,
        passed=passed,
        reason=reason,
    )


def evaluate_eligibility(
    scheme_id: str,
    scheme_name: str,
    rules: List[Dict[str, str]],
    required_slots: List[str],
    profile: Dict[str, Any],
) -> EligibilityDecision:
    """
    Run all rules for a scheme against a profile dict.

    Args:
        scheme_id: The scheme identifier.
        scheme_name: Human-readable scheme name.
        rules: List of rule dicts with keys:
               field_name, operator, value, value_type, description
        required_slots: List of slot names needed for this scheme.
        profile: Dict of {slot_name: value} — the user's filled profile.

    Returns:
        EligibilityDecision with full audit trail.
    """
    # Find missing required slots
    missing = [s for s in required_slots if s not in profile or profile[s] is None]

    rule_results: List[RuleResult] = []
    for rule in rules:
        result = _evaluate_rule(
            field_name=rule["field_name"],
            operator=rule["operator"],
            expected_raw=str(rule["value"]),
            value_type=rule["value_type"],
            profile=profile,
        )
        rule_results.append(result)

    failed = [r for r in rule_results if not r.passed]
    matched = len(rule_results) - len(failed)
    eligible = len(failed) == 0 and len(missing) == 0

    if eligible:
        explanation = f"You meet all {len(rule_results)} eligibility conditions for {scheme_name}."
    elif missing:
        explanation = (
            f"We still need some information to check eligibility: "
            f"{', '.join(missing)}."
        )
    else:
        first_fail = failed[0]
        explanation = (
            f"You do not meet the eligibility criteria for {scheme_name}. "
            f"Reason: {first_fail.reason}."
        )

    return EligibilityDecision(
        scheme_id=scheme_id,
        scheme_name=scheme_name,
        eligible=eligible,
        matched_rules=matched,
        total_rules=len(rule_results),
        failed_rules=failed,
        missing_slots=missing,
        explanation=explanation,
    )
