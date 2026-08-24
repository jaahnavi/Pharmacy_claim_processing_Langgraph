"""Node 3: evaluate_coverage — rules + LLM Call 1."""

from __future__ import annotations

from typing import Any

from app.graph.rules import evaluate_rules
from app.graph.state import ClaimState
from app.llm.coverage_rationale import generate_coverage_rationale


def evaluate_coverage(state: ClaimState) -> dict[str, Any]:
    member = state.get("member") or {}
    drug = state.get("drug") or {}
    request = state.get("request") or {}

    decision = evaluate_rules(member, drug, request)
    rationale, llm1_ok = generate_coverage_rationale(decision, member, drug)
    coverage = {
        **decision,
        "rationale": rationale,
        "llm1_fallback": not llm1_ok,
    }
    # Guard: never allow LLM to change status (status already from rules)
    coverage["coverage_status"] = decision["rule_status"]

    return {
        "coverage": coverage,
        "llm1_ok": llm1_ok,
        "status": "coverage_evaluated",
        "messages": [f"evaluate_coverage: status={coverage['coverage_status']} llm1_ok={llm1_ok}"],
    }
