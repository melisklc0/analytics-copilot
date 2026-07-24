from __future__ import annotations

import asyncio
import json
from typing import Any

from analytics_copilot.schemas.query import TraceEvent
from analytics_copilot.services.models import QueryResult
from analytics_copilot.workflow.service import final_payload, stream_query_events


class _FakeGraph:
    """Replays a fixed list of astream `updates` chunks, ignoring config/mode."""

    def __init__(self, updates: list[dict[str, Any]]) -> None:
        self._updates = updates

    async def astream(
        self, state: dict[str, Any], config: dict[str, Any], stream_mode: str
    ):
        assert stream_mode == "updates"
        for update in self._updates:
            yield update


def _collect(graph: _FakeGraph) -> list[TraceEvent]:
    async def _run() -> list[TraceEvent]:
        return [e async for e in stream_query_events(graph, "q", {})]

    return asyncio.run(_run())


def test_happy_path_emits_nodes_then_final() -> None:
    query_result = QueryResult(
        rows=[{"category": "beauty", "revenue": 42}],
        row_count=1,
        elapsed_s=0.1,
        sql="SELECT category, revenue FROM mart_product_categories LIMIT 1",
    )
    updates: list[dict[str, Any]] = [
        {"sql_generator": {"sql": query_result.sql, "sql_rationale": "top category"}},
        {"sql_validator": {"validation_status": "valid", "validation_error": None}},
        {"sql_executor": {"query_result": query_result}},
        {
            "result_formatter": {
                "response": {
                    "answer": "Beauty leads with 42 in revenue.",
                    "sql": query_result.sql,
                    "rows": query_result.rows,
                    "row_count": 1,
                }
            }
        },
    ]

    events = _collect(_FakeGraph(updates))

    assert [(e.type, e.node) for e in events[:-1]] == [
        ("node", "sql_generator"),
        ("node", "sql_validator"),
        ("node", "sql_executor"),
        ("node", "result_formatter"),
    ]
    assert events[0].data["rationale"] == "top category"
    assert events[2].data["row_count"] == 1

    final = events[-1]
    assert final.type == "final"
    assert final.data["answer"] == "Beauty leads with 42 in revenue."
    assert final.data["row_count"] == 1
    assert final.data["error"] is None
    # Events must serialize cleanly for SSE.
    assert json.loads(final.model_dump_json())["type"] == "final"


def test_self_correction_bumps_attempt_and_final_carries_retry_count() -> None:
    updates: list[dict[str, Any]] = [
        {"sql_generator": {"sql": "SELECT bad", "sql_rationale": "first try"}},
        {
            "sql_validator": {
                "validation_status": "invalid",
                "validation_error": "JOIN not allowed",
            }
        },
        # Loop back: the generator increments retry_count on the retry pass.
        {"sql_generator": {"sql": "SELECT good", "retry_count": 1}},
        {"sql_validator": {"validation_status": "valid", "validation_error": None}},
    ]

    events = _collect(_FakeGraph(updates))
    validator_events = [e for e in events if e.node == "sql_validator"]

    assert validator_events[0].data["attempt"] == 1
    assert validator_events[0].data["status"] == "invalid"
    assert validator_events[1].data["attempt"] == 2
    assert events[-1].type == "final"
    assert events[-1].data["retry_count"] == 1


def test_final_payload_defaults_when_nothing_ran() -> None:
    payload = final_payload({})
    assert payload == {
        "answer": "",
        "sql": None,
        "rows": [],
        "row_count": 0,
        "retry_count": 0,
        "error": None,
    }
