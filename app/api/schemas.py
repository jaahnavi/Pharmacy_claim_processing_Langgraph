"""Pydantic API schemas."""

from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field


class ClaimIntakeRequest(BaseModel):
    member_id: str
    patient_name: Optional[str] = None
    date_of_service: Optional[str] = None
    pharmacy_npi: str
    prescriber_npi: Optional[str] = None
    ndc: Optional[str] = None
    drug_name: Optional[str] = None
    quantity: int = 30
    days_supply: int = 30
    daw_code: Optional[int] = 0
    bin: Optional[str] = None
    pcn: Optional[str] = None
    group_id: Optional[str] = None

    model_config = {"extra": "allow"}


class ReviewerDecisionRequest(BaseModel):
    reviewer_id: str = Field(..., examples=["rev-001"])
    comment: str = ""


class ClaimResponse(BaseModel):
    claim_id: str
    status: str
    disclaimer: str
    request: Optional[dict[str, Any]] = None
    member: Optional[dict[str, Any]] = None
    drug: Optional[dict[str, Any]] = None
    coverage: Optional[dict[str, Any]] = None
    provider: Optional[dict[str, Any]] = None
    reviewer_brief: Optional[str] = None
    llm_suggestion: Optional[str] = None
    llm_suggestion_note: Optional[str] = None
    approval_status: Optional[str] = None
    reviewer: Optional[dict[str, Any]] = None
    submission: Optional[dict[str, Any]] = None
    member_ok: Optional[bool] = None
    drug_ok: Optional[bool] = None
    provider_ok: Optional[bool] = None
    llm1_ok: Optional[bool] = None
    llm2_ok: Optional[bool] = None
    messages: Optional[list[str]] = None
    error: Optional[str] = None
    next_nodes: Optional[list[str]] = None
