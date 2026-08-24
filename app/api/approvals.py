"""Human approval / reject resume endpoints."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.api.schemas import ClaimResponse, ReviewerDecisionRequest
from app.services import claims as claim_service

router = APIRouter(prefix="/claims", tags=["approvals"])


@router.post("/{claim_id}/approve", response_model=ClaimResponse)
def approve_claim(claim_id: str, body: ReviewerDecisionRequest) -> dict:
    result = claim_service.resume_decision(
        claim_id, decision="approve", reviewer_id=body.reviewer_id, comment=body.comment
    )
    if result is None:
        raise HTTPException(status_code=404, detail="Claim not found")
    return result


@router.post("/{claim_id}/reject", response_model=ClaimResponse)
def reject_claim(claim_id: str, body: ReviewerDecisionRequest) -> dict:
    result = claim_service.resume_decision(
        claim_id, decision="reject", reviewer_id=body.reviewer_id, comment=body.comment
    )
    if result is None:
        raise HTTPException(status_code=404, detail="Claim not found")
    return result


@router.post("/{claim_id}/request-changes", response_model=ClaimResponse)
def request_changes(claim_id: str, body: ReviewerDecisionRequest) -> dict:
    result = claim_service.resume_decision(
        claim_id,
        decision="request_changes",
        reviewer_id=body.reviewer_id,
        comment=body.comment,
    )
    if result is None:
        raise HTTPException(status_code=404, detail="Claim not found")
    return result
