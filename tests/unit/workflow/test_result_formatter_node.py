import asyncio
import pathlib
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
import yaml
from langchain_core.runnables import RunnableLambda

from analytics_copilot.services.models import QueryResult
from analytics_copilot.workflow.models import ResultOutput
from analytics_copilot.workflow.nodes.result_formatter import (
    ResultFormatterNode,
    _ROWS_PREVIEW_LIMIT,
)
from analytics_copilot.workflow.state import WorkflowState


@pytest.fixture
def prompts_dir(tmp_path: pathlib.Path) -> pathlib.Path:
    (tmp_path / "result_formatter.yaml").write_text(
        yaml.dump(
            {
                "system": "Summarise results.",
                "user": "{question}\n{sql}\n{row_count}\n{rows_preview}",
            }
        )
    )
    return tmp_path


def _make_query_result(
    rows: list[dict] | None = None,
    sql: str = "SELECT id FROM mart_customers LIMIT 10",
) -> QueryResult:
    rows = rows or [{"id": "1", "name": "Alice"}]
    return QueryResult(rows=rows, row_count=len(rows), elapsed_s=0.05, sql=sql)


def _make_node(
    prompts_dir: pathlib.Path,
    answer: str = "There is 1 customer.",
    side_effect: Exception | None = None,
) -> tuple[ResultFormatterNode, list[Any]]:
    captured: list[Any] = []

    async def fake_llm(prompt_value: Any) -> ResultOutput:
        captured.append(prompt_value)
        if side_effect is not None:
            raise side_effect
        return ResultOutput(answer=answer)

    mock_chain = RunnableLambda(fake_llm)
    mock_llm = MagicMock()
    mock_llm.with_structured_output = MagicMock(return_value=mock_chain)
    node = ResultFormatterNode(llm=mock_llm, prompts_dir=prompts_dir)
    return node, captured


def _base_state(**overrides: Any) -> WorkflowState:
    base: WorkflowState = {
        "question": "Who are the top customers?",
        "mart_context": None,
        "sql": "SELECT id FROM mart_customers LIMIT 10",
        "validation_status": "valid",
        "validation_error": None,
        "query_result": _make_query_result(),
        "retry_count": 0,
        "error": None,
        "response": None,
    }
    return {**base, **overrides}  # type: ignore[return-value]


_EMPTY_CONFIG: dict[str, Any] = {}


def test_returns_llm_answer_in_response(prompts_dir: pathlib.Path) -> None:
    node, _ = _make_node(prompts_dir, answer="There is 1 customer.")
    result = asyncio.run(node(_base_state(), _EMPTY_CONFIG))
    assert result["response"]["answer"] == "There is 1 customer."


def test_response_contains_sql_from_query_result(prompts_dir: pathlib.Path) -> None:
    sql = "SELECT id FROM mart_customers LIMIT 5"
    qr = _make_query_result(sql=sql)
    node, _ = _make_node(prompts_dir)
    result = asyncio.run(node(_base_state(query_result=qr), _EMPTY_CONFIG))
    assert result["response"]["sql"] == sql


def test_response_contains_rows_and_row_count(prompts_dir: pathlib.Path) -> None:
    rows = [{"id": str(i)} for i in range(3)]
    qr = _make_query_result(rows=rows)
    node, _ = _make_node(prompts_dir)
    result = asyncio.run(node(_base_state(query_result=qr), _EMPTY_CONFIG))
    assert result["response"]["rows"] == rows
    assert result["response"]["row_count"] == 3


def test_none_query_result_skips_llm_and_returns_fallback(
    prompts_dir: pathlib.Path,
) -> None:
    node, captured = _make_node(prompts_dir)
    result = asyncio.run(node(_base_state(query_result=None), _EMPTY_CONFIG))
    assert captured == []
    assert result["response"]["answer"] == "No results were returned."
    assert result["response"]["rows"] == []
    assert result["response"]["row_count"] == 0


def test_none_query_result_uses_state_sql_as_fallback(
    prompts_dir: pathlib.Path,
) -> None:
    node, _ = _make_node(prompts_dir)
    result = asyncio.run(
        node(_base_state(query_result=None, sql="SELECT 1"), _EMPTY_CONFIG)
    )
    assert result["response"]["sql"] == "SELECT 1"


def test_rows_preview_capped_at_limit(prompts_dir: pathlib.Path) -> None:
    rows = [{"id": str(i)} for i in range(_ROWS_PREVIEW_LIMIT + 10)]
    qr = _make_query_result(rows=rows)
    node, captured = _make_node(prompts_dir)
    asyncio.run(node(_base_state(query_result=qr), _EMPTY_CONFIG))
    assert len(captured) == 1
    # The prompt JSON preview contains exactly _ROWS_PREVIEW_LIMIT "id" keys
    assert str(captured[0]).count('"id"') == _ROWS_PREVIEW_LIMIT


def test_all_rows_returned_in_response_even_above_preview_limit(
    prompts_dir: pathlib.Path,
) -> None:
    rows = [{"id": str(i)} for i in range(_ROWS_PREVIEW_LIMIT + 5)]
    qr = _make_query_result(rows=rows)
    node, _ = _make_node(prompts_dir)
    result = asyncio.run(node(_base_state(query_result=qr), _EMPTY_CONFIG))
    assert len(result["response"]["rows"]) == _ROWS_PREVIEW_LIMIT + 5


def test_question_forwarded_to_llm_prompt(prompts_dir: pathlib.Path) -> None:
    node, captured = _make_node(prompts_dir)
    asyncio.run(node(_base_state(question="Show me top customers."), _EMPTY_CONFIG))
    assert "Show me top customers." in str(captured[0])


# --- Langfuse / config propagation ---


def _make_node_with_chain_spy(
    prompts_dir: pathlib.Path,
    answer: str = "There is 1 customer.",
) -> tuple[ResultFormatterNode, AsyncMock]:
    """Returns the node and a spy on _chain.ainvoke to capture the config argument."""
    mock_llm = MagicMock()
    mock_llm.with_structured_output = MagicMock(return_value=MagicMock())
    node = ResultFormatterNode(llm=mock_llm, prompts_dir=prompts_dir)
    chain_spy = MagicMock()
    chain_spy.ainvoke = AsyncMock(return_value=ResultOutput(answer=answer))
    node._chain = chain_spy  # type: ignore[assignment]
    return node, chain_spy.ainvoke


def test_config_forwarded_to_chain_ainvoke(prompts_dir: pathlib.Path) -> None:
    """The RunnableConfig (carrying the Langfuse CallbackHandler) must reach ainvoke
    so the LLM call is recorded under the same trace as the sql_generator span."""
    node, spy = _make_node_with_chain_spy(prompts_dir)
    langfuse_config = {"callbacks": [MagicMock()]}
    asyncio.run(node(_base_state(), langfuse_config))
    spy.assert_called_once()
    _, forwarded_config = spy.call_args.args
    assert forwarded_config is langfuse_config


def test_config_not_forwarded_when_query_result_is_none(
    prompts_dir: pathlib.Path,
) -> None:
    """Fallback path must not call the LLM at all — no spurious Langfuse span."""
    node, spy = _make_node_with_chain_spy(prompts_dir)
    langfuse_config = {"callbacks": [MagicMock()]}
    asyncio.run(node(_base_state(query_result=None), langfuse_config))
    spy.assert_not_called()
