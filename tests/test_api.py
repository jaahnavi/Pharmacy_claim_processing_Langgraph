"""Pytest suite for pharmacy claim orchestration."""

from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient
from langgraph.checkpoint.memory import MemorySaver

# Force template LLM fallbacks in CI / local without keys
os.environ.setdefault("LLM_FORCE_FALLBACK", "true")
os.environ.setdefault("CHECKPOINT_DB_PATH", ":memory:")

from app.graph.graph import build_graph, reset_graph_cache
from app.graph.rules import evaluate_rules
from app.main import app
from app.services import claims as claim_service


@pytest.fixture(autouse=True)
def _memory_graph(monkeypatch):
    """Use in-memory checkpointer for isolated tests."""
    reset_graph_cache()
    graph = build_graph(checkpointer=MemorySaver())
    monkeypatch.setattr(claim_service, "get_compiled_graph", lambda: graph)
    # also patch module-level cache used by API
    from app.graph import graph as graph_mod

    monkeypatch.setattr(graph_mod, "get_compiled_graph", lambda: graph)
    yield
    reset_graph_cache()


@pytest.fixture
def client():
    return TestClient(app)


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"
    assert "disclaimer" in r.json()


def test_get_member(client):
    r = client.get("/members/MEM-10001")
    assert r.status_code == 200
    assert r.json()["plan_id"] == "PLAN-GOLD"


def test_happy_path_approve(client):
    intake = client.post(
        "/claims/intake",
        json={
            "member_id": "MEM-10001",
            "patient_name": "Alex Demo",
            "date_of_service": "2026-07-15",
            "pharmacy_npi": "1679576722",
            "prescriber_npi": "1679576722",
            "drug_name": "atorvastatin",
            "quantity": 30,
            "days_supply": 30,
        },
    )
    assert intake.status_code == 200
    body = intake.json()
    assert body["status"] == "awaiting_human_approval"
    assert body["coverage"]["rationale"]
    assert body["reviewer_brief"]
    assert body["coverage"]["coverage_status"] == body["coverage"]["rule_status"]

    approve = client.post(
        f"/claims/{body['claim_id']}/approve",
        json={"reviewer_id": "rev-001", "comment": "ok"},
    )
    assert approve.status_code == 200
    final = approve.json()
    assert final["status"] == "submitted"
    assert final["submission"]["confirmation_id"]


def test_reject_no_submit(client):
    intake = client.post(
        "/claims/intake",
        json={
            "member_id": "MEM-10001",
            "pharmacy_npi": "1679576722",
            "prescriber_npi": "1679576722",
            "drug_name": "atorvastatin",
            "quantity": 30,
            "days_supply": 30,
        },
    )
    claim_id = intake.json()["claim_id"]
    reject = client.post(
        f"/claims/{claim_id}/reject",
        json={"reviewer_id": "rev-001", "comment": "no"},
    )
    assert reject.json()["status"] == "human_rejected"
    assert not (reject.json().get("submission") or {}).get("confirmation_id")


def test_unknown_member_no_llm(client):
    intake = client.post(
        "/claims/intake",
        json={
            "member_id": "MEM-UNKNOWN",
            "pharmacy_npi": "1679576722",
            "prescriber_npi": "1679576722",
            "drug_name": "atorvastatin",
            "quantity": 30,
            "days_supply": 30,
        },
    )
    body = intake.json()
    assert body["member_ok"] is False
    assert body["status"] == "member_not_found"
    assert not body.get("coverage")


def test_rules_non_override():
    member = {
        "member_id": "MEM-10001",
        "plan_id": "PLAN-GOLD",
        "active": True,
        "copay_preferred": 10.0,
    }
    drug = {"name": "atorvastatin", "generic_name": "atorvastatin"}
    decision = evaluate_rules(member, drug, {"quantity": 30, "days_supply": 30})
    assert decision["coverage_status"] == decision["rule_status"] == "covered"


def test_prior_auth_rule():
    member = {"member_id": "MEM-10003", "plan_id": "PLAN-SILVER", "active": True}
    drug = {"name": "Humira", "drug_name": "Humira"}
    decision = evaluate_rules(member, drug, {"quantity": 2, "days_supply": 28})
    assert decision["coverage_status"] == "prior_auth_required"


def test_submit_blocked_without_approval():
    from app.graph.nodes.submit_claim import submit_claim

    out = submit_claim({"approval_status": "pending", "claim_id": "x"})
    assert out["status"] == "submit_blocked"
