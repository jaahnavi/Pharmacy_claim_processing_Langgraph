"""openFDA Drug NDC public API client."""

from __future__ import annotations

from typing import Any, Optional

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from app.config import get_settings


def _normalize_ndc(ndc: str) -> list[str]:
    cleaned = ndc.replace("-", "").strip()
    variants = [cleaned]
    # common 5-4-1 / 5-3-2 style with dashes for search
    if len(cleaned) == 11:
        variants.append(f"{cleaned[:5]}-{cleaned[5:9]}-{cleaned[9:]}")
        variants.append(f"{cleaned[:5]}-{cleaned[5:8]}-{cleaned[8:]}")
    elif len(cleaned) == 10:
        variants.append(f"{cleaned[:5]}-{cleaned[5:9]}-{cleaned[9:]}")
    return variants


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=0.5, min=0.5, max=4), reraise=True)
def lookup_ndc(ndc: str) -> Optional[dict[str, Any]]:
    settings = get_settings()
    with httpx.Client(timeout=settings.http_timeout_seconds) as client:
        for variant in _normalize_ndc(ndc):
            # try product_ndc then package_ndc
            for field in ("product_ndc", "package_ndc"):
                params = {"search": f'{field}:"{variant}"', "limit": 1}
                try:
                    resp = client.get(settings.openfda_base_url, params=params)
                    if resp.status_code == 404:
                        continue
                    resp.raise_for_status()
                    data = resp.json()
                except httpx.HTTPStatusError:
                    continue
                results = (data or {}).get("results") or []
                if not results:
                    continue
                row = results[0]
                ingredients = row.get("active_ingredients") or []
                return {
                    "ndc": variant,
                    "brand_name": row.get("brand_name"),
                    "generic_name": row.get("generic_name"),
                    "labeler_name": row.get("labeler_name"),
                    "dosage_form": row.get("dosage_form"),
                    "product_type": row.get("product_type"),
                    "route": row.get("route"),
                    "active_ingredients": ingredients,
                    "name": row.get("brand_name") or row.get("generic_name"),
                    "source": "openfda",
                    "openfda_snippet": {
                        "brand_name": row.get("brand_name"),
                        "generic_name": row.get("generic_name"),
                        "dosage_form": row.get("dosage_form"),
                        "labeler_name": row.get("labeler_name"),
                    },
                }
    return None


@retry(stop=stop_after_attempt(2), wait=wait_exponential(multiplier=0.5, min=0.5, max=3), reraise=True)
def lookup_by_name(drug_name: str) -> Optional[dict[str, Any]]:
    settings = get_settings()
    params = {"search": f'brand_name:"{drug_name}"', "limit": 1}
    with httpx.Client(timeout=settings.http_timeout_seconds) as client:
        try:
            resp = client.get(settings.openfda_base_url, params=params)
            if resp.status_code == 404:
                params = {"search": f'generic_name:"{drug_name}"', "limit": 1}
                resp = client.get(settings.openfda_base_url, params=params)
            if resp.status_code == 404:
                return None
            resp.raise_for_status()
            data = resp.json()
        except httpx.HTTPStatusError:
            return None
    results = (data or {}).get("results") or []
    if not results:
        return None
    row = results[0]
    return {
        "brand_name": row.get("brand_name"),
        "generic_name": row.get("generic_name"),
        "labeler_name": row.get("labeler_name"),
        "dosage_form": row.get("dosage_form"),
        "active_ingredients": row.get("active_ingredients") or [],
        "name": row.get("brand_name") or row.get("generic_name") or drug_name,
        "source": "openfda",
        "openfda_snippet": {
            "brand_name": row.get("brand_name"),
            "generic_name": row.get("generic_name"),
            "dosage_form": row.get("dosage_form"),
        },
    }
