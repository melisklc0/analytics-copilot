import asyncio
from typing import Any

from analytics_copilot.workflow.graph import build_graph


def _initial_state(question: str = "What are the top customers?") -> dict[str, Any]:
    return {
        "question": question,
        "mart_context": None,
        "sql": None,
        "validation_status": None,
        "validation_error": None,
        "query_result": None,
        "retry_count": 0,
        "error": None,
        "response": None,
    }


def test_build_graph_compiles() -> None:
    graph = build_graph()
    assert graph is not None


def test_graph_smoke_pass_through() -> None:
    graph = build_graph()
    result = asyncio.run(graph.ainvoke(_initial_state()))
    assert result["response"] is not None


def test_graph_preserves_question() -> None:
    graph = build_graph()
    question = "How many orders were placed last month?"
    result = asyncio.run(graph.ainvoke(_initial_state(question)))
    assert result["question"] == question
