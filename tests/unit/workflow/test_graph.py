import asyncio
from typing import Any
from unittest.mock import MagicMock

from analytics_copilot.workflow.graph import build_graph


def _make_graph() -> Any:
    mock_manifest = MagicMock()
    mock_manifest.models = {}
    mock_executor = MagicMock()
    return build_graph(manifest=mock_manifest, executor=mock_executor)


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
    assert _make_graph() is not None


def test_graph_smoke_stub_generator_reaches_error_handler() -> None:
    graph = _make_graph()
    result = asyncio.run(graph.ainvoke(_initial_state()))
    assert result["response"] is not None


def test_graph_preserves_question() -> None:
    graph = _make_graph()
    question = "How many orders were placed last month?"
    result = asyncio.run(graph.ainvoke(_initial_state(question)))
    assert result["question"] == question
