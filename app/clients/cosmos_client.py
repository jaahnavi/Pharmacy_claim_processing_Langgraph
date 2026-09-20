"""Azure Cosmos DB (NoSQL API) client for persisting finalized claims."""

from __future__ import annotations

import logging
from functools import lru_cache
from typing import Any

logger = logging.getLogger(__name__)


@lru_cache
def _get_container():
    from app.config import get_settings

    settings = get_settings()
    if not settings.azure_cosmos_endpoint or not settings.azure_cosmos_key:
        logger.warning("Azure Cosmos DB is not configured (AZURE_COSMOS_ENDPOINT / AZURE_COSMOS_KEY missing)")
        return None

    from azure.cosmos import CosmosClient, PartitionKey

    client = CosmosClient(settings.azure_cosmos_endpoint, credential=settings.azure_cosmos_key)
    database = client.create_database_if_not_exists(settings.azure_cosmos_database)
    return database.create_container_if_not_exists(
        id=settings.azure_cosmos_container,
        partition_key=PartitionKey(path="/claim_id"),
    )


def save_claim(document: dict[str, Any]) -> bool:
    """Upsert the finalized claim document into Cosmos DB. Returns True on success."""
    container = _get_container()
    if container is None:
        return False

    doc = dict(document)
    doc["id"] = doc.get("claim_id")
    try:
        container.upsert_item(doc)
        return True
    except Exception:
        logger.exception("Failed to persist claim %s to Cosmos DB", document.get("claim_id"))
        return False
