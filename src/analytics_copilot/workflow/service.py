"""Workflow orchestration for the API.

Routers stay thin (CLAUDE.md): everything about *how* to drive the LangGraph
workflow — the initial state, node-by-node streaming, and shaping the terminal
state into the response — lives here. Routers only parse the request and map
these neutral results to HTTP DTOs.

The workflow is a plain-state StateGraph (no messages, no checkpointer), so the
streaming path merges node updates locally to reconstruct the terminal state.
"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from typing import Any

from analytics_copilot.schemas.query import TraceEvent

log = logging.getLogger(__name__)


def initial_state(question: str) -> dict[str, Any]:
    """The fresh WorkflowState the graph starts every run from."""
    return {
        "question": question,
        "mart_context": None,
        "sql": None,
        "sql_rationale": None,
        "validation_status": None,
        "validation_error": None,
        "query_result": None,
        "retry_count": 0,
        "error": None,
        "response": None,
    }


def final_payload(state: dict[str, Any]) -> dict[str, Any]:
    """Shape a terminal workflow state into the QueryResponse fields."""
    query_result = state.get("query_result")
    response = state.get("response") or {}
    return {
        "answer": str(response.get("answer", "")),
        "sql": state.get("sql"),
        "rows": list(query_result.rows) if query_result else [],
        "row_count": int(query_result.row_count) if query_result else 0,
        "retry_count": int(state.get("retry_count", 0)),
        "error": state.get("error"),
    }


def _node_view(node: str, state: dict[str, Any]) -> dict[str, Any]:
    """The public, JSON-safe slice a node produced, read from merged state.

    Reading from the merged state (not the raw update) means each event carries
    the latest values — e.g. ``attempt`` reflects self-corrections so far.
    """
    attempt = int(state.get("retry_count", 0)) + 1
    if node == "sql_generator":
        return {
            "attempt": attempt,
            "sql": state.get("sql"),
            "rationale": state.get("sql_rationale"),
            "error": state.get("error"),
        }
    if node == "sql_validator":
        return {
            "attempt": attempt,
            "status": state.get("validation_status"),
            "validation_error": state.get("validation_error"),
        }
    if node == "sql_executor":
        query_result = state.get("query_result")
        return {
            "row_count": int(query_result.row_count) if query_result else 0,
            "error": state.get("error"),
        }
    if node in ("result_formatter", "error_handler"):
        response = state.get("response") or {}
        return {"answer": str(response.get("answer", ""))}
    return {}


async def stream_query_events(
    graph: Any, question: str, config: dict[str, Any]
) -> AsyncIterator[TraceEvent]:
    """Drive the workflow and yield a TraceEvent per node, then a final event.

    ``stream_mode="updates"`` surfaces each node's partial state as it finishes.
    On a validation failure the graph loops back to ``sql_generator``, so the
    client sees the self-correction live: repeated generator/validator events
    with a rising ``attempt``. The graph has no checkpointer, so the terminal
    state is rebuilt by merging updates in order (plain TypedDict → last wins).
    """
    state = initial_state(question)
    async for update in graph.astream(state, config, stream_mode="updates"):
        for node, node_update in update.items():
            state.update(node_update)
            yield TraceEvent(type="node", node=node, data=_node_view(node, state))
    log.info(
        "query stream completed",
        extra={"sql": state.get("sql"), "error": state.get("error")},
    )
    yield TraceEvent(type="final", data=final_payload(state))
