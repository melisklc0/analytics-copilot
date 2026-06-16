import asyncio
from unittest.mock import AsyncMock, MagicMock

from analytics_copilot.core.exceptions import QueryTimeoutError, SQLExecutionError
from analytics_copilot.services.models import QueryResult
from analytics_copilot.workflow.nodes.sql_executor import SQLExecutorNode
from analytics_copilot.workflow.state import WorkflowState


def _state(**overrides: object) -> WorkflowState:
    base: WorkflowState = {
        "question": "top customers?",
        "mart_context": None,
        "sql": "SELECT customer_id FROM mart_customers LIMIT 10",
        "validation_status": "valid",
        "validation_error": None,
        "query_result": None,
        "retry_count": 0,
        "error": None,
        "response": None,
    }
    return {**base, **overrides}  # type: ignore[return-value]


def _run(coro):  # type: ignore[no-untyped-def]
    return asyncio.run(coro)


def _make_result(rows: list[dict] | None = None) -> QueryResult:
    return QueryResult(
        rows=rows or [{"customer_id": "abc"}],
        row_count=len(rows or [{"customer_id": "abc"}]),
        elapsed_s=0.05,
        sql="SELECT customer_id FROM mart_customers LIMIT 10",
    )


class TestSQLExecutorNode:
    def test_successful_execution_returns_query_result(self) -> None:
        mock_executor = MagicMock()
        expected = _make_result()
        mock_executor.run = AsyncMock(return_value=expected)
        node = SQLExecutorNode(mock_executor)

        result = _run(node(_state()))

        assert result["query_result"] == expected
        assert result.get("error") is None

    def test_timeout_sets_error_and_clears_query_result(self) -> None:
        mock_executor = MagicMock()
        mock_executor.run = AsyncMock(side_effect=QueryTimeoutError(10_000))
        node = SQLExecutorNode(mock_executor)

        result = _run(node(_state()))

        assert result["error"] is not None
        assert "timeout" in result["error"].lower()
        assert result["query_result"] is None

    def test_execution_error_sets_error_and_clears_query_result(self) -> None:
        mock_executor = MagicMock()
        mock_executor.run = AsyncMock(side_effect=SQLExecutionError("syntax error"))
        node = SQLExecutorNode(mock_executor)

        result = _run(node(_state()))

        assert result["error"] is not None
        assert result["query_result"] is None

    def test_none_sql_returns_error_without_calling_executor(self) -> None:
        mock_executor = MagicMock()
        node = SQLExecutorNode(mock_executor)

        result = _run(node(_state(sql=None)))

        assert result["error"] is not None
        mock_executor.run.assert_not_called()

    def test_executor_receives_exact_sql(self) -> None:
        mock_executor = MagicMock()
        mock_executor.run = AsyncMock(return_value=_make_result())
        node = SQLExecutorNode(mock_executor)
        sql = "SELECT customer_id FROM mart_customers LIMIT 5"

        _run(node(_state(sql=sql)))

        mock_executor.run.assert_called_once_with(sql)
