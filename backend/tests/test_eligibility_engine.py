"""
Jan Vaani — Eligibility Engine Tests

Tests the deterministic eligibility engine in isolation (no LLM, no DB).
These are the tests judges should look at to verify the engine works correctly.

Run with: pytest tests/ -v
"""
import pytest
from app.services.eligibility_engine import evaluate_eligibility, EligibilityDecision

# ── PM-KISAN Rules (mirrors schemes_seed.json) ────────────────
PM_KISAN_ID = "PM-KISAN-001"
PM_KISAN_NAME = "PM-KISAN"
PM_KISAN_RULES = [
    {"field_name": "occupation", "operator": "in", "value": '["farmer", "agriculture", "kisan", "किसान"]', "value_type": "list"},
    {"field_name": "land_size_acres", "operator": "<=", "value": "4.94", "value_type": "number"},
    {"field_name": "has_bank_account", "operator": "==", "value": "true", "value_type": "boolean"},
    {"field_name": "has_aadhaar", "operator": "==", "value": "true", "value_type": "boolean"},
    {"field_name": "is_income_tax_payer", "operator": "==", "value": "false", "value_type": "boolean"},
]
PM_KISAN_REQUIRED_SLOTS = [
    "occupation", "land_size_acres", "has_bank_account", "has_aadhaar", "is_income_tax_payer"
]

# ── PMAY-G Rules ───────────────────────────────────────────────
PMAY_G_ID = "PMAY-G-001"
PMAY_G_NAME = "PMAY-G"
PMAY_G_RULES = [
    {"field_name": "house_type", "operator": "in", "value": '["kutcha", "homeless", "no_house", "कच्चा", "बेघर"]', "value_type": "list"},
    {"field_name": "residence_type", "operator": "==", "value": "rural", "value_type": "string"},
    {"field_name": "annual_income", "operator": "<=", "value": "180000", "value_type": "number"},
    {"field_name": "has_aadhaar", "operator": "==", "value": "true", "value_type": "boolean"},
    {"field_name": "has_bank_account", "operator": "==", "value": "true", "value_type": "boolean"},
]
PMAY_G_REQUIRED_SLOTS = [
    "house_type", "residence_type", "annual_income", "has_aadhaar", "has_bank_account"
]


# ─────────────────────────────────────────────────────────────
# PM-KISAN Tests
# ─────────────────────────────────────────────────────────────

def test_pm_kisan_eligible_farmer_small_land():
    """A farmer with 2 acres of land and all documents should be eligible."""
    profile = {
        "occupation": "farmer",
        "land_size_acres": 2.0,
        "has_bank_account": True,
        "has_aadhaar": True,
        "is_income_tax_payer": False,
    }
    result = evaluate_eligibility(PM_KISAN_ID, PM_KISAN_NAME, PM_KISAN_RULES, PM_KISAN_REQUIRED_SLOTS, profile)
    assert result.eligible is True
    assert result.matched_rules == result.total_rules
    assert len(result.failed_rules) == 0
    assert len(result.missing_slots) == 0


def test_pm_kisan_not_eligible_too_much_land():
    """A farmer with 6 acres (> 4.94) should NOT be eligible."""
    profile = {
        "occupation": "farmer",
        "land_size_acres": 6.0,
        "has_bank_account": True,
        "has_aadhaar": True,
        "is_income_tax_payer": False,
    }
    result = evaluate_eligibility(PM_KISAN_ID, PM_KISAN_NAME, PM_KISAN_RULES, PM_KISAN_REQUIRED_SLOTS, profile)
    assert result.eligible is False
    assert any(r.field_name == "land_size_acres" for r in result.failed_rules)


def test_pm_kisan_not_eligible_income_tax_payer():
    """An income tax payer should NOT be eligible, even if all other criteria match."""
    profile = {
        "occupation": "farmer",
        "land_size_acres": 1.5,
        "has_bank_account": True,
        "has_aadhaar": True,
        "is_income_tax_payer": True,    # disqualifier
    }
    result = evaluate_eligibility(PM_KISAN_ID, PM_KISAN_NAME, PM_KISAN_RULES, PM_KISAN_REQUIRED_SLOTS, profile)
    assert result.eligible is False
    failed_fields = [r.field_name for r in result.failed_rules]
    assert "is_income_tax_payer" in failed_fields


def test_pm_kisan_not_eligible_wrong_occupation():
    """A shopkeeper (not a farmer) should NOT be eligible."""
    profile = {
        "occupation": "shopkeeper",
        "land_size_acres": 1.0,
        "has_bank_account": True,
        "has_aadhaar": True,
        "is_income_tax_payer": False,
    }
    result = evaluate_eligibility(PM_KISAN_ID, PM_KISAN_NAME, PM_KISAN_RULES, PM_KISAN_REQUIRED_SLOTS, profile)
    assert result.eligible is False
    failed_fields = [r.field_name for r in result.failed_rules]
    assert "occupation" in failed_fields


def test_pm_kisan_hindi_occupation_eligible():
    """A farmer who identifies as 'किसान' (Hindi) should be eligible."""
    profile = {
        "occupation": "किसान",
        "land_size_acres": 1.0,
        "has_bank_account": True,
        "has_aadhaar": True,
        "is_income_tax_payer": False,
    }
    result = evaluate_eligibility(PM_KISAN_ID, PM_KISAN_NAME, PM_KISAN_RULES, PM_KISAN_REQUIRED_SLOTS, profile)
    assert result.eligible is True


def test_pm_kisan_missing_slots():
    """An incomplete profile (missing land_size_acres) should not be eligible."""
    profile = {
        "occupation": "farmer",
        "has_bank_account": True,
        "has_aadhaar": True,
        "is_income_tax_payer": False,
        # land_size_acres missing
    }
    result = evaluate_eligibility(PM_KISAN_ID, PM_KISAN_NAME, PM_KISAN_RULES, PM_KISAN_REQUIRED_SLOTS, profile)
    assert result.eligible is False
    assert "land_size_acres" in result.missing_slots


def test_pm_kisan_exactly_at_land_limit():
    """A farmer with exactly 4.94 acres (the limit) should be eligible (<=)."""
    profile = {
        "occupation": "farmer",
        "land_size_acres": 4.94,
        "has_bank_account": True,
        "has_aadhaar": True,
        "is_income_tax_payer": False,
    }
    result = evaluate_eligibility(PM_KISAN_ID, PM_KISAN_NAME, PM_KISAN_RULES, PM_KISAN_REQUIRED_SLOTS, profile)
    assert result.eligible is True


def test_pm_kisan_no_bank_account():
    """Without a bank account, should not be eligible."""
    profile = {
        "occupation": "farmer",
        "land_size_acres": 2.0,
        "has_bank_account": False,
        "has_aadhaar": True,
        "is_income_tax_payer": False,
    }
    result = evaluate_eligibility(PM_KISAN_ID, PM_KISAN_NAME, PM_KISAN_RULES, PM_KISAN_REQUIRED_SLOTS, profile)
    assert result.eligible is False


# ─────────────────────────────────────────────────────────────
# PMAY-G Tests
# ─────────────────────────────────────────────────────────────

def test_pmay_g_eligible_kutcha_rural():
    """A rural resident with kutcha house and low income should be eligible."""
    profile = {
        "house_type": "kutcha",
        "residence_type": "rural",
        "annual_income": 120000,
        "has_aadhaar": True,
        "has_bank_account": True,
    }
    result = evaluate_eligibility(PMAY_G_ID, PMAY_G_NAME, PMAY_G_RULES, PMAY_G_REQUIRED_SLOTS, profile)
    assert result.eligible is True


def test_pmay_g_not_eligible_urban_resident():
    """An urban resident should NOT be eligible for PMAY-G (Gramin = rural)."""
    profile = {
        "house_type": "kutcha",
        "residence_type": "urban",
        "annual_income": 100000,
        "has_aadhaar": True,
        "has_bank_account": True,
    }
    result = evaluate_eligibility(PMAY_G_ID, PMAY_G_NAME, PMAY_G_RULES, PMAY_G_REQUIRED_SLOTS, profile)
    assert result.eligible is False
    failed_fields = [r.field_name for r in result.failed_rules]
    assert "residence_type" in failed_fields


def test_pmay_g_not_eligible_income_too_high():
    """A rural family with income > 1.8L should NOT be eligible."""
    profile = {
        "house_type": "kutcha",
        "residence_type": "rural",
        "annual_income": 250000,
        "has_aadhaar": True,
        "has_bank_account": True,
    }
    result = evaluate_eligibility(PMAY_G_ID, PMAY_G_NAME, PMAY_G_RULES, PMAY_G_REQUIRED_SLOTS, profile)
    assert result.eligible is False
    failed_fields = [r.field_name for r in result.failed_rules]
    assert "annual_income" in failed_fields


def test_pmay_g_homeless_eligible():
    """A homeless rural person should be eligible."""
    profile = {
        "house_type": "homeless",
        "residence_type": "rural",
        "annual_income": 60000,
        "has_aadhaar": True,
        "has_bank_account": True,
    }
    result = evaluate_eligibility(PMAY_G_ID, PMAY_G_NAME, PMAY_G_RULES, PMAY_G_REQUIRED_SLOTS, profile)
    assert result.eligible is True


def test_pmay_g_pucca_house_not_eligible():
    """Someone already living in a pucca house should NOT be eligible."""
    profile = {
        "house_type": "pucca",
        "residence_type": "rural",
        "annual_income": 100000,
        "has_aadhaar": True,
        "has_bank_account": True,
    }
    result = evaluate_eligibility(PMAY_G_ID, PMAY_G_NAME, PMAY_G_RULES, PMAY_G_REQUIRED_SLOTS, profile)
    assert result.eligible is False
    failed_fields = [r.field_name for r in result.failed_rules]
    assert "house_type" in failed_fields


# ─────────────────────────────────────────────────────────────
# String value casting tests
# ─────────────────────────────────────────────────────────────

def test_boolean_string_values():
    """Engine should accept string "true"/"false" as boolean profile values."""
    profile = {
        "occupation": "farmer",
        "land_size_acres": "2.5",
        "has_bank_account": "true",    # string, not bool
        "has_aadhaar": "yes",          # "yes" → True
        "is_income_tax_payer": "false",
    }
    result = evaluate_eligibility(PM_KISAN_ID, PM_KISAN_NAME, PM_KISAN_RULES, PM_KISAN_REQUIRED_SLOTS, profile)
    assert result.eligible is True


def test_number_string_values():
    """Engine should accept land_size_acres as a string representation."""
    profile = {
        "occupation": "kisan",         # alias for farmer
        "land_size_acres": "3",        # string number
        "has_bank_account": True,
        "has_aadhaar": True,
        "is_income_tax_payer": False,
    }
    result = evaluate_eligibility(PM_KISAN_ID, PM_KISAN_NAME, PM_KISAN_RULES, PM_KISAN_REQUIRED_SLOTS, profile)
    assert result.eligible is True


def test_explanation_present_on_failure():
    """Failed result should always contain a human-readable explanation."""
    profile = {
        "occupation": "teacher",
        "land_size_acres": 1.0,
        "has_bank_account": True,
        "has_aadhaar": True,
        "is_income_tax_payer": False,
    }
    result = evaluate_eligibility(PM_KISAN_ID, PM_KISAN_NAME, PM_KISAN_RULES, PM_KISAN_REQUIRED_SLOTS, profile)
    assert result.eligible is False
    assert len(result.explanation) > 0
    assert "occupation" in result.explanation.lower() or "teacher" in result.explanation.lower() or "eligib" in result.explanation.lower()
