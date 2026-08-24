"""Node 6: human_approval — HITL interrupt gate."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.graph.state import ClaimState


def human_approval(state: ClaimState) -> dict[str, Any]:
    decision = (state.get("human_decision") or state.get("approval_status") or "").lower()
    reviewer = dict(state.get("reviewer") or {})

    if decision in ("approve", "approved"):
        approval_status = "approved"
        status = "human_approved"
    elif decision in ("reject", "rejected"):
        approval_status = "rejected"
        status = "human_rejected"
    elif decision in ("request_changes", "changes_requested"):
        approval_status = "changes_requested"
        status = "human_changes_requested"
    else:
        return {
            "approval_status": "pending",
            "status": "awaiting_human_approval",
            "messages": ["human_approval: no decision present — remaining pending"],
            "error": "Human decision required before submit",
        }

    if not reviewer.get("decided_at"):
        reviewer["decided_at"] = datetime.now(timezone.utc).isoformat()
    reviewer["decision"] = approval_status

    return {
        "approval_status": approval_status,
        "reviewer": reviewer,
        "status": status,
        "messages": [
            f"human_approval: decision={approval_status} reviewer={reviewer.get('reviewer_id')} "
            f"(llm_suggestion was '{state.get('llm_suggestion')}' — suggestion only)"
        ],
        "error": None if approval_status == "approved" else state.get("error"),
    }
