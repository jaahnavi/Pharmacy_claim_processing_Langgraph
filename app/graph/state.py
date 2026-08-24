from typing import Any, Literal, Optional, TypedDict


class ClaimState(TypedDict, total=False):
    claim_id: str
    request: dict[str, Any]
    member: dict[str, Any]
    drug: dict[str, Any]
    coverage: dict[str, Any]  # status, reason_codes, rationale (LLM1), rule_status
    provider: dict[str, Any]
    reviewer_brief: str  # LLM2 output
    llm_suggestion: str  # approve | reject | request_changes (suggestion only)
    approval_status: Literal["pending", "approved", "rejected", "changes_requested"]
    reviewer: dict[str, Any]
    submission: dict[str, Any]
    status: str
    messages: list[str]
    error: Optional[str]
    member_ok: bool
    drug_ok: bool
    provider_ok: bool
    llm1_ok: bool
    llm2_ok: bool
    human_decision: Optional[str]
