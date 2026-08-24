"""Explicit fan-in join node — runs only after both parallel branches complete."""

from __future__ import annotations

from typing import Any

from app.graph.state import ClaimState


def fan_in_gate(state: ClaimState) -> dict[str, Any]:
    member_ok = bool(state.get("member_ok"))
    drug_ok = bool(state.get("drug_ok"))
    updates: dict[str, Any] = {
        "messages": [f"fan_in_gate: member_ok={member_ok} drug_ok={drug_ok}"],
    }
    if not member_ok:
        updates["status"] = state.get("status") or "member_not_found"
    elif not drug_ok:
        updates["status"] = state.get("status") or "drug_not_found"
    else:
        updates["status"] = "fan_in_ready"
    return updates
