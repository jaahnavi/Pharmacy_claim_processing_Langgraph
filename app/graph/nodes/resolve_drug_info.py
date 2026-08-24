"""Node 2: resolve_drug_info via RxNorm / openFDA (parallel branch)."""

from __future__ import annotations

from typing import Any

from app.clients import openfda, rxnorm
from app.graph.state import ClaimState


def resolve_drug_info(state: ClaimState) -> dict[str, Any]:
    request = state.get("request") or {}
    ndc = (request.get("ndc") or "").strip()
    drug_name = (request.get("drug_name") or "").strip()
    drug: dict[str, Any] = {}

    try:
        if ndc:
            fda = openfda.lookup_ndc(ndc)
            rx = rxnorm.lookup_by_ndc(ndc)
            if fda:
                drug = dict(fda)
                if rx:
                    drug["rxcui"] = rx.get("rxcui")
                    drug["source"] = "openfda+rxnorm"
                    if not drug.get("name"):
                        drug["name"] = rx.get("name")
            elif rx:
                drug = dict(rx)
            elif drug_name:
                drug = _resolve_by_name(drug_name) or {}
        elif drug_name:
            drug = _resolve_by_name(drug_name) or {}
        else:
            return {
                "drug": {"found": False},
                "drug_ok": False,
                "status": "drug_not_found",
                "error": "No NDC or drug_name provided",
                "messages": ["resolve_drug_info: no ndc or drug_name provided"],
            }
    except Exception as exc:
        return {
            "drug": {"found": False, "error": str(exc)},
            "drug_ok": False,
            "status": "drug_not_found",
            "error": f"Drug API error (fail closed): {exc}",
            "messages": [f"resolve_drug_info: api_error {exc}"],
        }

    if not drug or not (drug.get("name") or drug.get("rxcui") or drug.get("generic_name")):
        return {
            "drug": {"found": False, "ndc": ndc or None, "query_name": drug_name or None},
            "drug_ok": False,
            "status": "drug_not_found",
            "error": f"Drug not found for ndc={ndc or None} name={drug_name or None}",
            "messages": [f"resolve_drug_info: drug_not_found ndc={ndc} name={drug_name}"],
        }

    if drug_name and not drug.get("drug_name"):
        drug["drug_name"] = drug_name
    drug["found"] = True
    if ndc and not drug.get("ndc"):
        drug["ndc"] = ndc.replace("-", "")
    return {
        "drug": drug,
        "drug_ok": True,
        "messages": [f"resolve_drug_info: ok name={drug.get('name')} source={drug.get('source')}"],
    }


def _resolve_by_name(drug_name: str) -> dict[str, Any] | None:
    rx = rxnorm.lookup_by_name(drug_name)
    if rx:
        try:
            fda = openfda.lookup_by_name(drug_name)
            if fda:
                merged = dict(rx)
                for k, v in fda.items():
                    if v and k not in ("source",):
                        merged.setdefault(k, v)
                merged["source"] = "rxnorm+openfda"
                return merged
        except Exception:
            pass
        return rx
    try:
        return openfda.lookup_by_name(drug_name)
    except Exception:
        return None
