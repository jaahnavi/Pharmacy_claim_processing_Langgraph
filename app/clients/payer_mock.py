"""Mock payer claim submission."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

_SUBMISSIONS: dict[str, dict[str, Any]] = {}


def submit_claim_payload(payload: dict[str, Any]) -> dict[str, Any]:
    confirmation_id = f"CONF-{uuid.uuid4().hex[:12].upper()}"
    result = {
        "confirmation_id": confirmation_id,
        "status": "submitted",
        "submitted_at": datetime.now(timezone.utc).isoformat(),
        "payer_response_code": "A",
        "message": "Claim accepted by mock payer (educational demo).",
        "payload_echo": {
            "claim_id": payload.get("claim_id"),
            "member_id": (payload.get("member") or {}).get("member_id"),
            "drug_name": (payload.get("drug") or {}).get("name"),
            "coverage_status": (payload.get("coverage") or {}).get("coverage_status"),
        },
    }
    _SUBMISSIONS[confirmation_id] = result
    return result


def get_submission(confirmation_id: str) -> dict[str, Any] | None:
    return _SUBMISSIONS.get(confirmation_id)
