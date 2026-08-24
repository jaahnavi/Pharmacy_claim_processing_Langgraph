"""Claims intake and status endpoints."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.api.schemas import ClaimIntakeRequest, ClaimResponse
from app.services import claims as claim_service

router = APIRouter(prefix="/claims", tags=["claims"])


@router.post("/intake", response_model=ClaimResponse)
def intake_claim(body: ClaimIntakeRequest) -> dict:
    if not body.ndc and not body.drug_name:
        raise HTTPException(status_code=400, detail="Provide ndc and/or drug_name")
    result = claim_service.start_claim(body.model_dump())
    return result


@router.get("/{claim_id}", response_model=ClaimResponse)
def get_claim(claim_id: str) -> dict:
    result = claim_service.get_claim(claim_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Claim not found")
    return result
