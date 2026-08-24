"""LangGraph pharmacy claim orchestration graph.

Join pattern (fan-out / fan-in):
  START fans out to fetch_member_record AND resolve_drug_info in parallel.
  Both nodes edge into a virtual join via edges into evaluate_coverage gated by
  after_fan_in routing from a join node that waits until both branches finish.

  Implementation: LangGraph runs both branches from START concurrently when
  multiple edges leave START. A dedicated `fan_in_gate` node is reachable from
  both branches; LangGraph's reducer merges state, then conditional edges route
  to evaluate_coverage or END.

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
            "__end__": END,
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
            "__end__": END,
        },
    )
    builder.add_edge("submit_claim", END)

    return builder.compile(
        checkpointer=checkpointer,
        interrupt_before=["human_approval"],
    )


_memory_checkpointer: Optional[MemorySaver] = None
_sqlite_cm = None


def get_checkpointer():
    """Prefer SQLite for durable HITL resume; fall back to in-memory."""
    global _memory_checkpointer, _sqlite_cm
    settings = get_settings()
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
