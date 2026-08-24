"""Node 4: lookup_provider via CMS NPI Registry."""

from __future__ import annotations

from typing import Any

from app.clients import npi_registry
from app.graph.state import ClaimState


def lookup_provider(state: ClaimState) -> dict[str, Any]:
    request = state.get("request") or {}
    pharmacy_npi = (request.get("pharmacy_npi") or "").strip()
    prescriber_npi = (request.get("prescriber_npi") or "").strip()

    pharmacy = None
    prescriber = None
    errors: list[str] = []

    try:
        if pharmacy_npi:
            pharmacy = npi_registry.lookup_npi(pharmacy_npi)
            if pharmacy is None:
                errors.append(f"pharmacy_npi_not_found:{pharmacy_npi}")
            elif not pharmacy.get("active", True):
                errors.append(f"pharmacy_npi_inactive:{pharmacy_npi}")
        else:
            errors.append("pharmacy_npi_missing")
    except Exception as exc:
        errors.append(f"pharmacy_npi_api_error:{exc}")

    try:
        if prescriber_npi:
            if pharmacy_npi and prescriber_npi == pharmacy_npi and pharmacy:
                prescriber = pharmacy
            else:
                prescriber = npi_registry.lookup_npi(prescriber_npi)
            if prescriber is None:
                errors.append(f"prescriber_npi_not_found:{prescriber_npi}")
            elif not prescriber.get("active", True):
                errors.append(f"prescriber_npi_inactive:{prescriber_npi}")
    except Exception as exc:
        errors.append(f"prescriber_npi_api_error:{exc}")

    primary = pharmacy or prescriber or {}
    provider_ok = pharmacy is not None and (prescriber is not None or not prescriber_npi)

    coverage = dict(state.get("coverage") or {})
    if not provider_ok:
        coverage["coverage_status"] = "needs_review"
        codes = list(coverage.get("reason_codes") or [])
        if "R6_PROVIDER_NPI_INVALID" not in codes:
            codes.append("R6_PROVIDER_NPI_INVALID")
        coverage["reason_codes"] = codes
        coverage["recommended_action"] = "request_changes"
        provider = {
            "npi": pharmacy_npi or prescriber_npi,
            "pharmacy": pharmacy,
            "prescriber": prescriber,
            "name": primary.get("name"),
            "ok": False,
            "errors": errors,
            "source": "npi_registry",
            "status": "provider_not_found" if not primary else "provider_inactive",
        }
        return {
            "provider": provider,
            "provider_ok": False,
            "coverage": coverage,
            "status": "provider_needs_review",
            "messages": [f"lookup_provider: needs_review errors={errors}"],
            "error": "; ".join(errors) if errors else "provider_not_found",
        }

    provider = {
        "npi": pharmacy_npi,
        "pharmacy": pharmacy,
        "prescriber": prescriber,
        "name": (pharmacy or {}).get("name") or (prescriber or {}).get("name"),
        "taxonomy": (pharmacy or {}).get("taxonomy") or (prescriber or {}).get("taxonomy"),
        "credential": (prescriber or {}).get("credential"),
        "enumeration_type": (pharmacy or {}).get("enumeration_type"),
        "address": (pharmacy or {}).get("address") or (prescriber or {}).get("address"),
        "active": True,
        "ok": True,
        "source": "npi_registry",
    }
    return {
        "provider": provider,
        "provider_ok": True,
        "status": "provider_verified",
        "messages": [f"lookup_provider: ok npi={pharmacy_npi}"],
    }
