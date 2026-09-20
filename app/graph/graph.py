"""LangGraph pharmacy claim orchestration graph.

Join pattern (fan-out / fan-in):
  START fans out to fetch_member_record AND resolve_drug_info in parallel.
  Both nodes edge into a virtual join via edges into evaluate_coverage gated by
  after_fan_in routing from a join node that waits until both branches finish.

  Implementation: LangGraph runs both branches from START concurrently when
  multiple edges leave START. A dedicated `fan_in_gate` node is reachable from
  both branches; LangGraph's reducer merges state, then conditional edges route
  to evaluate_coverage or finalize_claim (terminal persistence, then END).

HITL: interrupt_before=["human_approval"] so the graph pauses after
draft_reviewer_brief with both LLM outputs available for the examiner.
"""

from __future__ import annotations

import sqlite3
from functools import lru_cache
from pathlib import Path
from typing import Annotated, Any, Optional

from langgraph.checkpoint.memory import MemorySaver
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import END, START, StateGraph

from app.config import get_settings
from app.graph.nodes.draft_reviewer_brief import draft_reviewer_brief
from app.graph.nodes.evaluate_coverage import evaluate_coverage
from app.graph.nodes.fan_in_gate import fan_in_gate
from app.graph.nodes.fetch_member_record import fetch_member_record
from app.graph.nodes.finalize_claim import finalize_claim
from app.graph.nodes.human_approval import human_approval
from app.graph.nodes.lookup_provider import lookup_provider
from app.graph.nodes.resolve_drug_info import resolve_drug_info
from app.graph.nodes.submit_claim import submit_claim
from app.graph.routing import after_fan_in, after_human_approval
from app.graph.state import ClaimState


def _merge_messages(left: Optional[list], right: Optional[list]) -> list:
    """Append-only reducer so parallel branches do not clobber each other."""
    return list(left or []) + list(right or [])


class GraphState(ClaimState, total=False):
    """ClaimState with reducers for parallel branch merges."""

    messages: Annotated[list, _merge_messages]


def build_graph(checkpointer=None):
    builder = StateGraph(GraphState)

    builder.add_node("fetch_member_record", fetch_member_record)
    builder.add_node("resolve_drug_info", resolve_drug_info)
    builder.add_node("fan_in_gate", fan_in_gate)
    builder.add_node("evaluate_coverage", evaluate_coverage)
    builder.add_node("lookup_provider", lookup_provider)
    builder.add_node("draft_reviewer_brief", draft_reviewer_brief)
    builder.add_node("human_approval", human_approval)
    builder.add_node("submit_claim", submit_claim)
    builder.add_node("finalize_claim", finalize_claim)

    # Fan-out: parallel from START
    builder.add_edge(START, "fetch_member_record")
    builder.add_edge(START, "resolve_drug_info")

    # Fan-in: both branches join at fan_in_gate
    builder.add_edge("fetch_member_record", "fan_in_gate")
    builder.add_edge("resolve_drug_info", "fan_in_gate")

    builder.add_conditional_edges(
        "fan_in_gate",
        after_fan_in,
        {
            "evaluate_coverage": "evaluate_coverage",
            "__end__": "finalize_claim",
        },
    )

    builder.add_edge("evaluate_coverage", "lookup_provider")
    # Invalid NPI still continues to draft_reviewer_brief (needs_review path)
    builder.add_edge("lookup_provider", "draft_reviewer_brief")
    builder.add_edge("draft_reviewer_brief", "human_approval")

    builder.add_conditional_edges(
        "human_approval",
        after_human_approval,
        {
            "submit_claim": "submit_claim",
            "__end__": "finalize_claim",
        },
    )
    builder.add_edge("submit_claim", "finalize_claim")
    # Every terminal path — fan-in failure, human reject/changes-requested, or a
    # successful submission — converges here, which persists the claim to
    # Cosmos DB before the run actually ends.
    builder.add_edge("finalize_claim", END)

    return builder.compile(
        checkpointer=checkpointer,
        interrupt_before=["human_approval"],
    )


_memory_checkpointer: Optional[MemorySaver] = None
_sqlite_cm = None
_blob_checkpointer = None


def _build_blob_checkpointer():
    """Durable checkpointer backed by Azure Blob Storage — safe for multiple app instances.

    Each checkpoint / pending-write is stored as its own blob under the
    configured container; see ``app.graph.checkpointer_blob.AzureBlobSaver``.
    The container is created on first use if it does not already exist.
    """
    global _blob_checkpointer
    if _blob_checkpointer is not None:
        return _blob_checkpointer

    from app.graph.checkpointer_blob import AzureBlobSaver

    settings = get_settings()
    if not settings.azure_storage_connection_string:
        raise RuntimeError("CHECKPOINT_BACKEND=blob but AZURE_STORAGE_CONNECTION_STRING is not set")

    _blob_checkpointer = AzureBlobSaver.from_connection_string(
        settings.azure_storage_connection_string,
        settings.azure_storage_checkpoint_container,
    )
    return _blob_checkpointer


def get_checkpointer():
    """Return the configured checkpointer.

    CHECKPOINT_BACKEND:
      - ``blob``    : durable + safe for multiple app instances (Azure Blob Storage; recommended for deploy)
      - ``sqlite``  : single-instance local file (default; fine for dev / HITL resume)
      - ``memory``  : ephemeral, lost on restart
    """
    global _memory_checkpointer, _sqlite_cm
    settings = get_settings()
    backend = (settings.checkpoint_backend or "sqlite").lower()

    if backend == "blob":
        return _build_blob_checkpointer()

    if backend == "memory":
        if _memory_checkpointer is None:
            _memory_checkpointer = MemorySaver()
        return _memory_checkpointer

    db_path = Path(settings.checkpoint_db_path)
    try:
        db_path.parent.mkdir(parents=True, exist_ok=True)
        # SqliteSaver.from_conn_string returns a context manager in recent versions
        conn = sqlite3.connect(str(db_path), check_same_thread=False)
        return SqliteSaver(conn)
    except Exception:
        if _memory_checkpointer is None:
            _memory_checkpointer = MemorySaver()
        return _memory_checkpointer


@lru_cache
def get_compiled_graph():
    return build_graph(checkpointer=get_checkpointer())


def reset_graph_cache() -> None:
    get_compiled_graph.cache_clear()
