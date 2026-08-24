"""CMS NPI Registry public API client."""

from __future__ import annotations

from typing import Any, Optional

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from app.config import get_settings


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=0.5, min=0.5, max=4), reraise=True)
def lookup_npi(npi: str) -> Optional[dict[str, Any]]:
    settings = get_settings()
    number = (npi or "").strip()
    if not number.isdigit() or len(number) != 10:
        return None
    params = {"number": number, "version": "2.1"}
    with httpx.Client(timeout=settings.http_timeout_seconds) as client:
        resp = client.get(settings.npi_registry_url, params=params)
        resp.raise_for_status()
        data = resp.json()
    results = (data or {}).get("results") or []
    if not results:
        return None
    row = results[0]
    basic = row.get("basic") or {}
    taxonomies = row.get("taxonomies") or []
    addresses = row.get("addresses") or []
    primary_tax = next((t for t in taxonomies if t.get("primary")), taxonomies[0] if taxonomies else {})
    loc = next((a for a in addresses if a.get("address_purpose") == "LOCATION"), addresses[0] if addresses else {})

    org = basic.get("organization_name")
    person = " ".join(
        p for p in [basic.get("name_prefix"), basic.get("first_name"), basic.get("last_name"), basic.get("credential")] if p
    ).strip()
    name = org or person or f"NPI-{number}"
    status = (basic.get("status") or "A").upper()
    return {
        "npi": number,
        "name": name,
        "enumeration_type": row.get("enumeration_type"),
        "credential": basic.get("credential"),
        "taxonomy": primary_tax.get("desc"),
        "taxonomy_code": primary_tax.get("code"),
        "address": {
            "line1": loc.get("address_1"),
            "city": loc.get("city"),
            "state": loc.get("state"),
            "postal_code": loc.get("postal_code"),
            "country": loc.get("country_code"),
        },
        "status": status,
        "active": status == "A",
        "source": "npi_registry",
    }
