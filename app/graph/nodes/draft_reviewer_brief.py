"""Node 5: draft_reviewer_brief — LLM Call 2."""

from __future__ import annotations

from typing import Any

from app.graph.state import ClaimState
from app.llm.reviewer_brief import generate_reviewer_brief


def draft_reviewer_brief(state: ClaimState) -> dict[str, Any]:
    brief, suggestion, llm2_ok = generate_reviewer_brief(
        member=state.get("member") or {},
        drug=state.get("drug") or {},
        coverage=state.get("coverage") or {},
        provider=state.get("provider") or {},
        request=state.get("request") or {},
    )
    return {
        "reviewer_brief": brief,
        "llm_suggestion": suggestion,
        "llm2_ok": llm2_ok,
        "approval_status": "pending",
        "status": "awaiting_human_approval",
        "messages": [f"draft_reviewer_brief: llm2_ok={llm2_ok} suggestion={suggestion}"],
    }
