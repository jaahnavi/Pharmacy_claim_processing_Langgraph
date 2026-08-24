"""Conditional routing helpers for the claim graph."""

from __future__ import annotations

from typing import Literal

from app.graph.state import ClaimState


def after_fan_in(state: ClaimState) -> Literal["evaluate_coverage", "__end__"]:
    """Join gate: both member and drug must succeed before coverage."""
    if not state.get("member_ok"):
        return "__end__"
    if not state.get("drug_ok"):
        return "__end__"
    return "evaluate_coverage"


def after_human_approval(state: ClaimState) -> Literal["submit_claim", "__end__"]:
    if state.get("approval_status") == "approved":
        return "submit_claim"
    return "__end__"
