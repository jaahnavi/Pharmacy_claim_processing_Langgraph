"""
Streamlit HITL approval UI (optional stretch).

Run:
  streamlit run ui/approval_app.py
"""

from __future__ import annotations

import os

import httpx
import streamlit as st

BASE = os.getenv("APP_BASE_URL", "http://localhost:8000")
DISCLAIMER = (
    "Educational demo only. Not for real insurance billing, medical advice, or PHI. "
    "Use synthetic member/claim data only."
)

st.set_page_config(page_title="Pharmacy Claim Reviewer", layout="wide")
st.title("Pharmacy Claim Examiner")
st.warning(DISCLAIMER)

with st.sidebar:
    st.subheader("Start claim")
    member_id = st.text_input("Member ID", "MEM-10001")
    drug_name = st.text_input("Drug name", "atorvastatin")
    pharmacy_npi = st.text_input("Pharmacy NPI", "1679576722")
    quantity = st.number_input("Quantity", min_value=1, value=30)
    if st.button("Intake claim"):
        payload = {
            "member_id": member_id,
            "patient_name": "Demo Patient",
            "date_of_service": "2026-07-15",
            "pharmacy_npi": pharmacy_npi,
            "prescriber_npi": pharmacy_npi,
            "drug_name": drug_name,
            "quantity": int(quantity),
            "days_supply": 30,
        }
        with httpx.Client(timeout=60) as client:
            r = client.post(f"{BASE}/claims/intake", json=payload)
            r.raise_for_status()
            st.session_state["claim"] = r.json()

claim = st.session_state.get("claim")
claim_id = st.text_input("Or load claim_id", claim.get("claim_id") if claim else "")
if st.button("Refresh claim") and claim_id:
    with httpx.Client(timeout=30) as client:
        r = client.get(f"{BASE}/claims/{claim_id}")
        r.raise_for_status()
        st.session_state["claim"] = r.json()
        claim = st.session_state["claim"]

if claim:
    st.subheader(f"Claim `{claim.get('claim_id')}` — {claim.get('status')}")
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("### Coverage (rules) + LLM Call 1 rationale")
        st.json(claim.get("coverage") or {})
        st.markdown("### Member")
        st.json(claim.get("member") or {})
        st.markdown("### Drug")
        st.json(claim.get("drug") or {})
    with c2:
        st.markdown("### Provider (NPI Registry)")
        st.json(claim.get("provider") or {})
        st.markdown("### LLM Call 2 — Reviewer brief")
        st.info(claim.get("reviewer_brief") or "(none)")
        st.caption(
            f"LLM suggestion (suggestion only): **{claim.get('llm_suggestion')}** — "
            "human decision is mandatory."
        )

    if claim.get("status") == "awaiting_human_approval":
        reviewer_id = st.text_input("Reviewer ID", "rev-001")
        comment = st.text_area("Comment", "Reviewed member, drug, coverage, NPI, and brief.")
        a, b, c = st.columns(3)
        with a:
            if st.button("Approve", type="primary"):
                with httpx.Client(timeout=60) as client:
                    r = client.post(
                        f"{BASE}/claims/{claim['claim_id']}/approve",
                        json={"reviewer_id": reviewer_id, "comment": comment},
                    )
                    r.raise_for_status()
                    st.session_state["claim"] = r.json()
                    st.rerun()
        with b:
            if st.button("Reject"):
                with httpx.Client(timeout=60) as client:
                    r = client.post(
                        f"{BASE}/claims/{claim['claim_id']}/reject",
                        json={"reviewer_id": reviewer_id, "comment": comment},
                    )
                    r.raise_for_status()
                    st.session_state["claim"] = r.json()
                    st.rerun()
        with c:
            if st.button("Request changes"):
                with httpx.Client(timeout=60) as client:
                    r = client.post(
                        f"{BASE}/claims/{claim['claim_id']}/request-changes",
                        json={"reviewer_id": reviewer_id, "comment": comment},
                    )
                    r.raise_for_status()
                    st.session_state["claim"] = r.json()
                    st.rerun()

    if claim.get("submission"):
        st.success(claim["submission"])
