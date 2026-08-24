"""Deterministic formulary / coverage adjudication rules.

Rules (documented in README):
  R1  Member active + drug on preferred list          -> covered
  R2  Specialty / high-cost drug class                -> prior_auth_required
  R3  Quantity > plan max for days supply             -> needs_review
  R4  Drug not resolved                               -> block at fan-in
  R5  Member missing/inactive                         -> block at fan-in
  R6  Provider NPI invalid                            -> needs_review (handled in lookup)
"""

from __future__ import annotations

from typing import Any

# Preferred formulary (generic / brand tokens, lowercase)
PREFERRED_DRUGS = {
    "atorvastatin",
    "lipitor",
    "metformin",
    "lisinopril",
    "amlodipine",
    "omeprazole",
    "sertraline",
    "levothyroxine",
}

# Specialty / high-cost — always prior auth
PRIOR_AUTH_DRUGS = {
    "humira",
    "adalimumab",
    "enbrel",
    "etanercept",
    "keytruda",
    "pembrolizumab",
    "ozempic",
    "semaglutide",
    "dupixent",
    "dupilumab",
}

# Plan quantity limits: max qty per days_supply window
PLAN_QTY_LIMITS = {
    "PLAN-GOLD": 90,
    "PLAN-SILVER": 60,
    "PLAN-BRONZE": 30,
    "default": 90,
}


def _drug_tokens(drug: dict[str, Any]) -> set[str]:
    tokens: set[str] = set()
    for key in ("name", "brand_name", "generic_name", "drug_name"):
        val = drug.get(key) or ""
        if isinstance(val, str) and val.strip():
            tokens.add(val.strip().lower())
    # also check request drug_name mirrored into drug
    for ing in drug.get("active_ingredients") or []:
        if isinstance(ing, str):
            tokens.add(ing.lower())
        elif isinstance(ing, dict) and ing.get("name"):
            tokens.add(str(ing["name"]).lower())
    return tokens


def evaluate_rules(member: dict[str, Any], drug: dict[str, Any], request: dict[str, Any]) -> dict[str, Any]:
    """Return machine coverage decision. LLM must not override these fields."""
    reason_codes: list[str] = []
    recommended_action = "approve"

    if not member.get("active", False):
        return {
            "coverage_status": "not_covered",
            "rule_status": "not_covered",
            "reason_codes": ["R5_MEMBER_INACTIVE"],
            "patient_pay_estimate": None,
            "recommended_action": "reject",
            "rules_applied": ["R5"],
        }

    tokens = _drug_tokens(drug)
    qty = int(request.get("quantity") or 0)
    days = int(request.get("days_supply") or 30)
    plan_id = member.get("plan_id") or "default"
    max_qty = PLAN_QTY_LIMITS.get(plan_id, PLAN_QTY_LIMITS["default"])

    is_pa = bool(tokens & PRIOR_AUTH_DRUGS)
    is_preferred = bool(tokens & PREFERRED_DRUGS)

    if is_pa:
        reason_codes.append("R2_SPECIALTY_PRIOR_AUTH")
        status = "prior_auth_required"
        recommended_action = "request_changes"
        patient_pay = 75.0
        rules = ["R2"]
    elif is_preferred and member.get("active"):
        reason_codes.append("R1_PREFERRED_FORMULARY")
        status = "covered"
        recommended_action = "approve"
        patient_pay = float(member.get("copay_preferred", 10.0))
        rules = ["R1"]
    else:
        reason_codes.append("R1_NOT_ON_PREFERRED")
        status = "needs_review"
        recommended_action = "request_changes"
        patient_pay = float(member.get("copay_nonpreferred", 45.0))
        rules = ["R1"]

    # Quantity rule can escalate to needs_review
    prorated_limit = max(1, int(max_qty * (days / 30.0)))
    if qty > prorated_limit:
        reason_codes.append("R3_QUANTITY_EXCEEDS_PLAN_MAX")
        status = "needs_review"
        recommended_action = "request_changes"
        rules = list(set(rules + ["R3"]))

    return {
        "coverage_status": status,
        "rule_status": status,  # immutable copy for non-override checks
        "reason_codes": reason_codes,
        "patient_pay_estimate": patient_pay,
        "recommended_action": recommended_action,
        "rules_applied": rules,
        "quantity_limit": prorated_limit,
    }


def get_formulary_rules() -> dict[str, Any]:
    return {
        "preferred_drugs": sorted(PREFERRED_DRUGS),
        "prior_auth_drugs": sorted(PRIOR_AUTH_DRUGS),
        "plan_qty_limits": PLAN_QTY_LIMITS,
        "rules": {
            "R1": "Member active + drug on preferred list -> covered",
            "R2": "Specialty / high-cost drug class -> prior_auth_required",
            "R3": "Quantity > plan max for days supply -> needs_review",
            "R4": "Drug not resolved -> block at fan-in",
            "R5": "Member missing/inactive -> block at fan-in",
            "R6": "Provider NPI invalid -> needs_review",
        },
    }
