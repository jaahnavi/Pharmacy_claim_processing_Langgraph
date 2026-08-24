"""LLM Call 1 — Coverage rationale generator (traced as llm_coverage_rationale)."""

from __future__ import annotations

import os
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from langsmith import traceable

from app.config import get_settings
from app.llm.client import get_chat_model, llm_configured


def _force_fallback() -> bool:
    settings = get_settings()
    env = os.getenv("LLM_FORCE_FALLBACK", "").lower() in {"1", "true", "yes"}
    return bool(settings.llm_force_fallback or env)


def template_rationale(coverage: dict[str, Any], member: dict[str, Any], drug: dict[str, Any]) -> str:
    status = coverage.get("coverage_status") or coverage.get("rule_status")
    codes = ", ".join(coverage.get("reason_codes") or []) or "none"
    pay = coverage.get("patient_pay_estimate")
    member_id = member.get("member_id", "unknown")
    plan = member.get("plan_id", "unknown")
    drug_name = drug.get("name") or drug.get("generic_name") or "unknown"
    return (
        f"Coverage decision '{status}' was produced by the deterministic rules engine "
        f"(reason codes: {codes}). Member {member_id} on plan {plan} was evaluated for "
        f"medication '{drug_name}'. Estimated patient pay is {pay}. "
        f"This rationale is a template fallback (LLM unavailable). "
        f"Do not treat as clinical advice. Educational demo only."
    )


PROMPT = """You are a pharmacy claims assistant for an educational demo.
Given the structured coverage decision below, write a short rationale (3-6 sentences)
for a human claims examiner. Do not change the decision. Do not invent member PHI.
Do not provide medical advice. Explain only the given decision using the provided facts.

Decision: {coverage_status}
Reason codes: {reason_codes}
Member plan summary: {member_summary}
Drug summary: {drug_summary}
Optional label snippet: {label_snippet}
"""


@traceable(name="llm_coverage_rationale", run_type="llm")
def generate_coverage_rationale(
    coverage: dict[str, Any],
    member: dict[str, Any],
    drug: dict[str, Any],
) -> tuple[str, bool]:
    """Return (rationale, llm_ok). Never changes coverage_status."""
    settings = get_settings()
    if _force_fallback() or not llm_configured():
        return template_rationale(coverage, member, drug), False

    member_summary = {
        "member_id": member.get("member_id"),
        "plan_id": member.get("plan_id"),
        "group_id": member.get("group_id"),
        "active": member.get("active"),
        "deductible_remaining": member.get("deductible_remaining"),
    }
    drug_summary = {
        "name": drug.get("name"),
        "rxcui": drug.get("rxcui"),
        "ndc": drug.get("ndc"),
        "generic_name": drug.get("generic_name"),
        "brand_name": drug.get("brand_name"),
        "source": drug.get("source"),
    }
    label_snippet = drug.get("openfda_snippet") or {}

    try:
        model = get_chat_model(temperature=settings.llm1_temperature)
        messages = [
            SystemMessage(
                content=(
                    "Explain the given coverage decision only. "
                    "Never change coverage_status. Never invent PHI or clinical advice."
                )
            ),
            HumanMessage(
                content=PROMPT.format(
                    coverage_status=coverage.get("coverage_status"),
                    reason_codes=", ".join(coverage.get("reason_codes") or []),
                    member_summary=member_summary,
                    drug_summary=drug_summary,
                    label_snippet=label_snippet,
                )
            ),
        ]
        result = model.invoke(messages)
        text = (result.content or "").strip()
        if not text:
            return template_rationale(coverage, member, drug), False
        return text, True
    except Exception:
        return template_rationale(coverage, member, drug), False
