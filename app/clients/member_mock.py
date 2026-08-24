"""Synthetic member records (demo only — no real PHI)."""

from __future__ import annotations

from typing import Any, Optional

MEMBERS: dict[str, dict[str, Any]] = {
    "MEM-10001": {
        "member_id": "MEM-10001",
        "patient_name": "Alex Demo",
        "plan_id": "PLAN-GOLD",
        "group_id": "GRP-AAA",
        "formulary_preference": "preferred_generic",
        "active": True,
        "deductible_remaining": 250.0,
        "copay_preferred": 10.0,
        "copay_nonpreferred": 40.0,
        "bin": "610014",
        "pcn": "DEMO",
    },
    "MEM-10002": {
        "member_id": "MEM-10002",
        "patient_name": "Jordan Demo",
        "plan_id": "PLAN-GOLD",
        "group_id": "GRP-AAA",
        "formulary_preference": "preferred_generic",
        "active": True,
        "deductible_remaining": 100.0,
        "copay_preferred": 10.0,
        "copay_nonpreferred": 40.0,
        "bin": "610014",
        "pcn": "DEMO",
    },
    "MEM-10003": {
        "member_id": "MEM-10003",
        "patient_name": "Sam Demo",
        "plan_id": "PLAN-SILVER",
        "group_id": "GRP-BBB",
        "formulary_preference": "specialty_managed",
        "active": True,
        "deductible_remaining": 500.0,
        "copay_preferred": 15.0,
        "copay_nonpreferred": 50.0,
        "bin": "610014",
        "pcn": "DEMO",
    },
    "MEM-10004": {
        "member_id": "MEM-10004",
        "patient_name": "Riley Demo",
        "plan_id": "PLAN-BRONZE",
        "group_id": "GRP-CCC",
        "formulary_preference": "preferred_generic",
        "active": False,
        "deductible_remaining": 0.0,
        "copay_preferred": 20.0,
        "copay_nonpreferred": 60.0,
        "bin": "610014",
        "pcn": "DEMO",
    },
    "MEM-10005": {
        "member_id": "MEM-10005",
        "patient_name": "Casey Demo",
        "plan_id": "PLAN-GOLD",
        "group_id": "GRP-AAA",
        "formulary_preference": "preferred_generic",
        "active": True,
        "deductible_remaining": 75.0,
        "copay_preferred": 10.0,
        "copay_nonpreferred": 40.0,
        "bin": "610014",
        "pcn": "DEMO",
    },
}


def get_member(member_id: str) -> Optional[dict[str, Any]]:
    record = MEMBERS.get(member_id)
    if record is None:
        return None
    return dict(record)
