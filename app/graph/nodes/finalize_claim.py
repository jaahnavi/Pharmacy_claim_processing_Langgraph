"""Terminal node: persist the final claim state to Azure Cosmos DB (NoSQL).

Every path out of the graph — fan-in failure, human rejection/changes
requested, or a successful submission — routes through this node before END,
so the claim is durably recorded in Cosmos DB regardless of how the run
terminated.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.clients.cosmos_client import save_claim
from app.graph.state import ClaimState


def finalize_claim(state: ClaimState) -> dict[str, Any]:
    document = {
        "claim_id": state.get("claim_id"),
        "request": state.get("request"),
        "member": state.get("member"),
        "drug": state.get("drug"),
        "coverage": state.get("coverage"),
        "provider": state.get("provider"),
        "reviewer_brief": state.get("reviewer_brief"),
        "llm_suggestion": state.get("llm_suggestion"),
        "approval_status": state.get("approval_status"),
        "reviewer": state.get("reviewer"),
        "submission": state.get("submission"),
        "status": state.get("status"),
        "error": state.get("error"),
        "finalized_at": datetime.now(timezone.utc).isoformat(),
    }
    persisted = save_claim(document)
    return {
        "messages": [f"finalize_claim: cosmos_persisted={persisted} status={state.get('status')}"],
    }
