"""Claim graph runner service — intake, status, approve/reject resume."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from app.config import get_settings
from app.graph.graph import get_compiled_graph


DISCLAIMER = None  # filled from settings at response time


def _disclaimer() -> str:
    return get_settings().disclaimer


def start_claim(request: dict[str, Any]) -> dict[str, Any]:
    claim_id = str(uuid.uuid4())
    graph = get_compiled_graph()
    initial: dict[str, Any] = {
        "claim_id": claim_id,
        "request": request,
        "approval_status": "pending",
        "messages": [f"intake: started claim_id={claim_id}"],
        "status": "started",
    }
    config = {"configurable": {"thread_id": claim_id}}
    # Run until HITL interrupt (or END on fan-in failure)
    result = graph.invoke(initial, config=config)
    return _public_view(claim_id, result)


def get_claim(claim_id: str) -> Optional[dict[str, Any]]:
    graph = get_compiled_graph()
    config = {"configurable": {"thread_id": claim_id}}
    snap = graph.get_state(config)
    if snap is None or snap.values is None or not snap.values:
        return None
    return _public_view(claim_id, dict(snap.values), next_nodes=list(snap.next or ()))


def resume_decision(
    claim_id: str,
    decision: str,
    reviewer_id: str,
    comment: str = "",
) -> Optional[dict[str, Any]]:
    graph = get_compiled_graph()
    config = {"configurable": {"thread_id": claim_id}}
    snap = graph.get_state(config)
    if snap is None or not snap.values:
        return None

    # Must be interrupted awaiting human_approval
    if "human_approval" not in (snap.next or ()):
        current = _public_view(claim_id, dict(snap.values), next_nodes=list(snap.next or ()))
        current["error"] = current.get("error") or "Claim is not awaiting human approval"
        return current

    decision_norm = decision.lower().strip()
    if decision_norm in ("approve", "approved"):
        approval_status = "approved"
        human_decision = "approve"
    elif decision_norm in ("reject", "rejected"):
        approval_status = "rejected"
        human_decision = "reject"
    elif decision_norm in ("request_changes", "changes_requested"):
        approval_status = "changes_requested"
        human_decision = "request_changes"
    else:
        raise ValueError(f"Invalid decision: {decision}")

    reviewer = {
        "reviewer_id": reviewer_id,
        "decision": approval_status,
        "comment": comment,
        "decided_at": datetime.now(timezone.utc).isoformat(),
    }

    graph.update_state(
        config,
        {
            "human_decision": human_decision,
            "approval_status": approval_status,
            "reviewer": reviewer,
        },
    )
    result = graph.invoke(None, config=config)
    return _public_view(claim_id, result)


def _public_view(
    claim_id: str,
    state: dict[str, Any],
    next_nodes: Optional[list] = None,
) -> dict[str, Any]:
    status = state.get("status") or "unknown"
    if next_nodes and "human_approval" in next_nodes:
        status = "awaiting_human_approval"

    return {
        "claim_id": claim_id,
        "status": status,
        "disclaimer": _disclaimer(),
        "request": state.get("request"),
        "member": state.get("member"),
        "drug": state.get("drug"),
        "coverage": state.get("coverage"),
        "provider": state.get("provider"),
        "reviewer_brief": state.get("reviewer_brief"),
        "llm_suggestion": state.get("llm_suggestion"),
        "llm_suggestion_note": "Suggestion only — human approval is mandatory; LLM never auto-submits.",
        "approval_status": state.get("approval_status"),
        "reviewer": state.get("reviewer"),
        "submission": state.get("submission"),
        "member_ok": state.get("member_ok"),
        "drug_ok": state.get("drug_ok"),
        "provider_ok": state.get("provider_ok"),
        "llm1_ok": state.get("llm1_ok"),
        "llm2_ok": state.get("llm2_ok"),
        "messages": state.get("messages"),
        "error": state.get("error"),
        "next_nodes": next_nodes,
    }
