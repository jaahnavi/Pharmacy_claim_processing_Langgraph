"""RxNorm public API client (NLM)."""

from __future__ import annotations

from typing import Any, Optional

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from app.config import get_settings


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=0.5, min=0.5, max=4), reraise=True)
def lookup_by_name(drug_name: str) -> Optional[dict[str, Any]]:
    settings = get_settings()
    url = f"{settings.rxnorm_base_url}/rxcui.json"
    with httpx.Client(timeout=settings.http_timeout_seconds) as client:
        resp = client.get(url, params={"name": drug_name})
        resp.raise_for_status()
        data = resp.json()
    id_group = (data or {}).get("idGroup") or {}
    rxnorm_ids = id_group.get("rxnormId") or []
    if not rxnorm_ids:
        return None
    rxcui = rxnorm_ids[0]
    props = _get_properties(rxcui)
    return {
        "rxcui": rxcui,
        "name": props.get("name") or drug_name,
        "synonym": props.get("synonym"),
        "tty": props.get("tty"),
        "source": "rxnorm",
        "brand_name": props.get("name"),
        "generic_name": props.get("name"),
    }


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=0.5, min=0.5, max=4), reraise=True)
def _get_properties(rxcui: str) -> dict[str, Any]:
    settings = get_settings()
    url = f"{settings.rxnorm_base_url}/rxcui/{rxcui}/properties.json"
    with httpx.Client(timeout=settings.http_timeout_seconds) as client:
        resp = client.get(url)
        resp.raise_for_status()
        data = resp.json()
    return (data or {}).get("properties") or {}


def lookup_by_ndc(ndc: str) -> Optional[dict[str, Any]]:
    """Resolve NDC via RxNorm ndcstatus, then fetch properties."""
    settings = get_settings()
    cleaned = ndc.replace("-", "").strip()
    url = f"{settings.rxnorm_base_url}/ndcstatus.json"
    try:
        with httpx.Client(timeout=settings.http_timeout_seconds) as client:
            resp = client.get(url, params={"ndc": cleaned})
            resp.raise_for_status()
            data = resp.json()
        status = (data or {}).get("ndcStatus") or {}
        rxcui = status.get("rxcui")
        if not rxcui:
            return None
        props = _get_properties(str(rxcui))
        return {
            "rxcui": str(rxcui),
            "name": props.get("name") or status.get("conceptName"),
            "ndc": cleaned,
            "source": "rxnorm",
            "brand_name": props.get("name"),
            "generic_name": props.get("name"),
            "tty": props.get("tty"),
        }
    except Exception:
        return None
