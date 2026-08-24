"""Members + payer mock endpoints."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Any

from app.clients import member_mock
from app.clients.payer_mock import submit_claim_payload
from app.graph.rules import get_formulary_rules

router = APIRouter(tags=["local-apis"])


@router.get("/members/{member_id}")
def get_member(member_id: str) -> dict[str, Any]:
    member = member_mock.get_member(member_id)
    if member is None:
        raise HTTPException(status_code=404, detail="Member not found")
    return member


class PayerSubmitBody(BaseModel):
    claim_id: str | None = None
    member: dict[str, Any] | None = None
    drug: dict[str, Any] | None = None
    coverage: dict[str, Any] | None = None
    provider: dict[str, Any] | None = None
    reviewer: dict[str, Any] | None = None
    request: dict[str, Any] | None = None

    model_config = {"extra": "allow"}


@router.post("/payer/submit")
def payer_submit(body: PayerSubmitBody) -> dict[str, Any]:
    return submit_claim_payload(body.model_dump())


@router.get("/payer/rules")
def payer_rules() -> dict[str, Any]:
    return get_formulary_rules()
