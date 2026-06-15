import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import psycopg
import psycopg.errors
import pytest

from analytics_copilot.core.config import Settings
from analytics_copilot.core.exceptions import QueryTimeoutError, SQLExecutionError
from analytics_copilot.services.sql_executor import (
    SQLExecutor,
    QueryResult,
    _apply_limit,
)


@pytest.fixture()
def settings() -> Settings:
    return Settings(
        postgres_host="localhost",
        postgres_port=5433,
        postgres_db="test_db",
        postgres_ro_user="analyst_ro",
        postgres_ro_password="secret",  # type: ignore[arg-type]
    )


@pytest.fixture()
def executor(settings: Settings) -> SQLExecutor:
    return SQLExecutor(settings=settings)


def _make_mock_conn(rows: list[dict]) -> AsyncMock:  # type: ignore[type-arg]
    mock_cursor = AsyncMock()
    # AsyncMock.__aenter__ defaults to a new AsyncMock, not self — set explicitly
    mock_cursor.__aenter__.return_value = mock_cursor
    mock_cursor.fetchall.return_value = rows

    mock_conn = AsyncMock()
    mock_conn.__aenter__.return_value = mock_conn
    # cursor() is synchronous in psycopg3 — override with MagicMock
    mock_conn.cursor = MagicMock(return_value=mock_cursor)
    return mock_conn


# ---------------------------------------------------------------------------
# _apply_limit
# ---------------------------------------------------------------------------


class TestApplyLimit:
    def test_adds_limit_when_absent(self) -> None:
        result = _apply_limit("SELECT * FROM mart_customers", 500)
        assert f"LIMIT {500}" in result

    def test_keeps_limit_when_smaller(self) -> None:
        result = _apply_limit("SELECT * FROM mart_customers LIMIT 10", 500)
        assert "LIMIT 10" in result
        assert f"LIMIT {500}" not in result

    def test_replaces_limit_when_larger(self) -> None:
        result = _apply_limit("SELECT * FROM mart_customers LIMIT 9999", 500)
        assert f"LIMIT {500}" in result
        assert "LIMIT 9999" not in result

    def test_strips_trailing_semicolon(self) -> None:
        result = _apply_limit("SELECT * FROM mart_customers;", 500)
        assert not result.rstrip().endswith(";")

    def test_limit_case_insensitive(self) -> None:
        result = _apply_limit("SELECT * FROM mart_customers limit 9999", 500)
        assert "9999" not in result


# ---------------------------------------------------------------------------
# SQLExecutor.run
# ---------------------------------------------------------------------------


class TestSQLExecutorRun:
    @patch(
        "analytics_copilot.services.sql_executor.psycopg.AsyncConnection.connect",
        new_callable=AsyncMock,
    )
    def test_returns_query_result(
        self, mock_connect: AsyncMock, executor: SQLExecutor
    ) -> None:
        sample_rows = [{"customer_id": "abc", "total_revenue": 99.5}]
        mock_connect.return_value = _make_mock_conn(sample_rows)

        result = asyncio.run(executor.run("SELECT * FROM mart_customers"))

        assert isinstance(result, QueryResult)
        assert result.rows == sample_rows
        assert result.row_count == 1

    @patch(
        "analytics_copilot.services.sql_executor.psycopg.AsyncConnection.connect",
        new_callable=AsyncMock,
    )
    def test_sql_has_limit_applied(
        self, mock_connect: AsyncMock, executor: SQLExecutor
    ) -> None:
        mock_conn = _make_mock_conn([])
        mock_connect.return_value = mock_conn

        asyncio.run(executor.run("SELECT * FROM mart_customers"))

        cursor = mock_conn.cursor.return_value
        executed_sql: str = cursor.execute.call_args[0][0]
        assert "LIMIT" in executed_sql.upper()

    @patch(
        "analytics_copilot.services.sql_executor.psycopg.AsyncConnection.connect",
        new_callable=AsyncMock,
    )
    def test_raises_query_timeout_error(
        self, mock_connect: AsyncMock, executor: SQLExecutor
    ) -> None:
        mock_cursor = AsyncMock()
        mock_cursor.__aenter__.return_value = mock_cursor
        mock_cursor.execute.side_effect = psycopg.errors.QueryCanceled()
        mock_conn = AsyncMock()
        mock_conn.__aenter__.return_value = mock_conn
        mock_conn.cursor = MagicMock(return_value=mock_cursor)
        mock_connect.return_value = mock_conn

        with pytest.raises(QueryTimeoutError):
            asyncio.run(executor.run("SELECT * FROM mart_customers"))

    @patch(
        "analytics_copilot.services.sql_executor.psycopg.AsyncConnection.connect",
        new_callable=AsyncMock,
    )
    def test_raises_sql_execution_error_on_operational_error(
        self, mock_connect: AsyncMock, executor: SQLExecutor
    ) -> None:
        mock_connect.side_effect = psycopg.OperationalError("connection refused")

        with pytest.raises(SQLExecutionError):
            asyncio.run(executor.run("SELECT * FROM mart_customers"))

    @patch(
        "analytics_copilot.services.sql_executor.psycopg.AsyncConnection.connect",
        new_callable=AsyncMock,
    )
    def test_raises_sql_execution_error_on_programming_error(
        self, mock_connect: AsyncMock, executor: SQLExecutor
    ) -> None:
        mock_cursor = AsyncMock()
        mock_cursor.__aenter__.return_value = mock_cursor
        mock_cursor.execute.side_effect = psycopg.ProgrammingError("syntax error")
        mock_conn = AsyncMock()
        mock_conn.__aenter__.return_value = mock_conn
        mock_conn.cursor = MagicMock(return_value=mock_cursor)
        mock_connect.return_value = mock_conn

        with pytest.raises(SQLExecutionError):
            asyncio.run(executor.run("SELECT * FROM mart_customers"))

    @patch(
        "analytics_copilot.services.sql_executor.psycopg.AsyncConnection.connect",
        new_callable=AsyncMock,
    )
    def test_result_sql_matches_executed_sql(
        self, mock_connect: AsyncMock, executor: SQLExecutor
    ) -> None:
        mock_connect.return_value = _make_mock_conn([])

        result = asyncio.run(executor.run("SELECT * FROM mart_customers"))

        assert "LIMIT" in result.sql.upper()

    @patch(
        "analytics_copilot.services.sql_executor.psycopg.AsyncConnection.connect",
        new_callable=AsyncMock,
    )
    def test_elapsed_s_is_non_negative(
        self, mock_connect: AsyncMock, executor: SQLExecutor
    ) -> None:
        mock_connect.return_value = _make_mock_conn([])

        result = asyncio.run(executor.run("SELECT * FROM mart_customers"))

        assert result.elapsed_s >= 0
