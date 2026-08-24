"""Node 1: fetch_member_record (parallel branch)."""

from __future__ import annotations

from typing import Any

from app.clients import member_mock
from app.graph.state import ClaimState


def fetch_member_record(state: ClaimState) -> dict[str, Any]:
    request = state.get("request") or {}
    member_id = request.get("member_id") or ""

    member = member_mock.get_member(member_id)
    if member is None:
        return {
            "member": {"member_id": member_id, "found": False},
            "member_ok": False,
            "status": "member_not_found",
            "error": f"Member not found: {member_id}",
            "messages": [f"fetch_member_record: member_not_found ({member_id})"],
        }

    if not member.get("active", False):
        member["found"] = True
        return {
            "member": member,
            "member_ok": False,
            "status": "member_inactive",
            "error": f"Member inactive: {member_id}",
            "messages": [f"fetch_member_record: member_inactive ({member_id})"],
        }

    member["found"] = True
    return {
        "member": member,
        "member_ok": True,
        "messages": [f"fetch_member_record: ok plan={member.get('plan_id')}"],
    }
