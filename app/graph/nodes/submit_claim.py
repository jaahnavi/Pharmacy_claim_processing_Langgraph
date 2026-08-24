"""Node 7: submit_claim — only after explicit human approve."""

from __future__ import annotations

from typing import Any

from app.clients.payer_mock import submit_claim_payload
from app.graph.state import ClaimState


def submit_claim(state: ClaimState) -> dict[str, Any]:
    approval = state.get("approval_status")

    if approval != "approved":
        return {
            "submission": {"blocked": True, "reason": "approval_required"},
            "status": "submit_blocked",
            "error": "Claim cannot be submitted without explicit human approve",
            "messages": [f"submit_claim: BLOCKED approval_status={approval}"],
        }

    payload = {
        "claim_id": state.get("claim_id"),
        "member": state.get("member"),
        "drug": state.get("drug"),
        "coverage": state.get("coverage"),
        "provider": state.get("provider"),
        "reviewer": state.get("reviewer"),
        "request": state.get("request"),
    }
    result = submit_claim_payload(payload)
    return {
        "submission": result,
        "status": "submitted",
        "messages": [f"submit_claim: submitted confirmation={result.get('confirmation_id')}"],
        "error": None,
    }
