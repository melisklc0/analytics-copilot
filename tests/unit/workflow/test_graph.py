import asyncio
import pathlib
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import yaml

from analytics_copilot.workflow.graph import build_graph
from analytics_copilot.workflow.models import ResultOutput, SQLOutput


def _write_prompts(tmp_path: pathlib.Path) -> None:
    (tmp_path / "sql_generator.yaml").write_text(
        yaml.dump(
            {
                "system": "Generate SQL.",
                "user": "{mart_context}\n{question}{retry_note}",
            }
        )
    )
    (tmp_path / "result_formatter.yaml").write_text(
        yaml.dump(
            {
                "system": "Summarise results.",
                "user": "{question}\n{sql}\n{row_count}\n{rows_preview}",
            }
        )
    )


def _make_graph(tmp_path: pathlib.Path) -> Any:
    _write_prompts(tmp_path)
    mock_manifest = MagicMock()
    mock_manifest.models = {}
    mock_manifest.get_all_models.return_value = []
    mock_manifest.get_context.return_value = ""
    mock_executor = MagicMock()
    mock_chain = MagicMock()
    mock_chain.ainvoke = AsyncMock(side_effect=Exception("Mock LLM error"))
    mock_llm = MagicMock()
    mock_llm.with_structured_output = MagicMock(return_value=mock_chain)
    return build_graph(
        manifest=mock_manifest,
        executor=mock_executor,
        llm=mock_llm,
        prompts_dir=tmp_path,
    )


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


def test_build_graph_compiles(tmp_path: pathlib.Path) -> None:
    assert _make_graph(tmp_path) is not None


def test_graph_reaches_error_handler_on_llm_failure(tmp_path: pathlib.Path) -> None:
    graph = _make_graph(tmp_path)
    result = asyncio.run(graph.ainvoke(_initial_state()))
    assert result["response"] is not None


def test_graph_preserves_question(tmp_path: pathlib.Path) -> None:
    graph = _make_graph(tmp_path)
    question = "How many orders were placed last month?"
    result = asyncio.run(graph.ainvoke(_initial_state(question)))
    assert result["question"] == question


def test_graph_happy_path_reaches_result_formatter(tmp_path: pathlib.Path) -> None:
    _write_prompts(tmp_path)
    mock_manifest = MagicMock()
    mock_manifest.models = {}
    mock_manifest.get_all_models.return_value = []
    mock_manifest.get_context.return_value = ""
    mock_executor = MagicMock()
    mock_executor.run = AsyncMock(
        return_value=MagicMock(rows=[], row_count=0, elapsed_s=0.1, sql="SELECT 1")
    )

    def _chain_for(schema: Any) -> MagicMock:
        chain = MagicMock()
        if schema is SQLOutput:
            chain.ainvoke = AsyncMock(return_value=SQLOutput(sql="SELECT 1"))
        else:
            chain.ainvoke = AsyncMock(return_value=ResultOutput(answer="1 row found."))
        return chain

    mock_llm = MagicMock()
    mock_llm.with_structured_output = MagicMock(side_effect=_chain_for)
    graph = build_graph(
        manifest=mock_manifest,
        executor=mock_executor,
        llm=mock_llm,
        prompts_dir=tmp_path,
    )
    result = asyncio.run(graph.ainvoke(_initial_state()))
    assert result["response"] is not None
