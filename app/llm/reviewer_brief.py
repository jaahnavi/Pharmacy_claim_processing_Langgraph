"""LLM Call 2 — Reviewer brief generator (traced as llm_reviewer_brief)."""

from __future__ import annotations

import json
import os
import re
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from langsmith import traceable

from app.config import get_settings
from app.llm.client import get_chat_model, llm_configured


def _force_fallback() -> bool:
    settings = get_settings()
    env = os.getenv("LLM_FORCE_FALLBACK", "").lower() in {"1", "true", "yes"}
    return bool(settings.llm_force_fallback or env)

SUGGESTION_VALUES = {"approve", "reject", "request_changes"}


def template_brief(
    member: dict[str, Any],
    drug: dict[str, Any],
    coverage: dict[str, Any],
    provider: dict[str, Any],
    request: dict[str, Any],
) -> tuple[str, str]:
    status = coverage.get("coverage_status")
    suggestion = coverage.get("recommended_action") or "request_changes"
    if suggestion not in SUGGESTION_VALUES:
        suggestion = "request_changes"
    brief = (
        f"Summary: Claim for member {member.get('member_id')} seeking "
        f"{drug.get('name') or request.get('drug_name')} with coverage_status={status}. "
        f"Provider NPI {provider.get('npi')} ({provider.get('name')}) verified={provider.get('ok', True)}. "
        f"Risks: Review reason codes {coverage.get('reason_codes')}; confirm quantity/days supply and NPI taxonomy. "
        f"Suggested action (suggestion only): {suggestion}. "
        f"Checklist: verify member active, drug identity (RxCUI/NDC), coverage rules, provider status. "
        f"Template fallback — educational demo only."
    )
    return brief, suggestion


def _parse_suggestion(text: str, fallback: str) -> str:
    m = re.search(r"suggested action\s*:\s*(approve|reject|request_changes)", text, re.I)
    if m:
        return m.group(1).lower()
    for val in SUGGESTION_VALUES:
        if re.search(rf"\b{val}\b", text, re.I):
            # prefer explicit line if possible
            pass
    # look for standalone suggestion token near end
    lower = text.lower()
    for val in ("request_changes", "approve", "reject"):
        if f"suggested action: {val}" in lower or f"suggested action:{val}" in lower:
            return val
    return fallback if fallback in SUGGESTION_VALUES else "request_changes"


@traceable(name="llm_reviewer_brief", run_type="llm")
def generate_reviewer_brief(
    member: dict[str, Any],
    drug: dict[str, Any],
    coverage: dict[str, Any],
    provider: dict[str, Any],
    request: dict[str, Any],
) -> tuple[str, str, bool]:
    """Return (brief, suggestion, llm_ok). Never auto-approves the claim."""
    settings = get_settings()
    fallback_brief, fallback_suggestion = template_brief(member, drug, coverage, provider, request)
    if _force_fallback() or not llm_configured():
        return fallback_brief, fallback_suggestion, False

    context = {
        "member": {
            "member_id": member.get("member_id"),
            "plan_id": member.get("plan_id"),
            "active": member.get("active"),
            "group_id": member.get("group_id"),
        },
        "drug": {
            "name": drug.get("name"),
            "rxcui": drug.get("rxcui"),
            "ndc": drug.get("ndc"),
            "source": drug.get("source"),
        },
        "coverage": {
            "coverage_status": coverage.get("coverage_status"),
            "reason_codes": coverage.get("reason_codes"),
            "patient_pay_estimate": coverage.get("patient_pay_estimate"),
            "rationale": coverage.get("rationale"),
        },
        "provider": {
            "npi": provider.get("npi"),
            "name": provider.get("name"),
            "taxonomy": provider.get("taxonomy"),
            "active": provider.get("active"),
            "ok": provider.get("ok"),
        },
        "claim_request": {
            "quantity": request.get("quantity"),
            "days_supply": request.get("days_supply"),
            "date_of_service": request.get("date_of_service"),
        },
    }

    prompt = (
        "You are preparing a claims examiner briefing packet for an educational demo.\n"
        "Using ONLY the JSON context provided, write:\n"
        "1) Summary (2 sentences)\n"
        "2) Risks / open questions (bullets)\n"
        "3) Suggested action: approve | reject | request_changes\n"
        "4) Verification checklist (bullets)\n"
        "Do not invent NPI, drug, or member facts. Label suggestion as suggestion only.\n"
        f"Context JSON: {json.dumps(context)}"
    )

    try:
        model = get_chat_model(temperature=settings.llm2_temperature)
        messages = [
            SystemMessage(content="Ground the brief strictly in the provided JSON. Never invent facts."),
            HumanMessage(content=prompt),
        ]
        result = model.invoke(messages)
        text = (result.content or "").strip()
        if not text:
            return fallback_brief, fallback_suggestion, False
        suggestion = _parse_suggestion(text, fallback_suggestion)
        return text, suggestion, True
    except Exception:
        return fallback_brief, fallback_suggestion, False
