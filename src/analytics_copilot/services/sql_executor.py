from __future__ import annotations

import logging
import time
from typing import Any

import psycopg
import psycopg.rows
import sqlglot
import sqlglot.expressions as exp

from analytics_copilot.core.config import Settings, get_settings
from analytics_copilot.core.exceptions import QueryTimeoutError, SQLExecutionError
from analytics_copilot.services.models import QueryResult

logger = logging.getLogger(__name__)


def _apply_limit(sql: str, max_rows: int) -> str:
    tree = sqlglot.parse_one(sql, dialect="postgres")
    limit_node = tree.args.get("limit")
    if limit_node:
        limit_expr = limit_node.args.get("expression")
        if isinstance(limit_expr, exp.Literal) and int(limit_expr.this) <= max_rows:
            return tree.sql(dialect="postgres")
    tree.args["limit"] = exp.Limit(expression=exp.Literal.number(max_rows))
    return tree.sql(dialect="postgres")


class SQLExecutor:
    """Async, read-only SQL executor backed by the configured read-only PostgreSQL role."""

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()

    def _connect_kwargs(self) -> dict[str, Any]:
        s = self._settings
        return {
            "host": s.postgres_host,
            "port": s.postgres_port,
            "dbname": s.postgres_db,
            "user": s.postgres_ro_user,
            "password": s.postgres_ro_password.get_secret_value(),
            "options": f"-c statement_timeout={s.sql_statement_timeout_ms}",
            "autocommit": True,
        }

    async def run(self, sql: str) -> QueryResult:
        """Execute *sql* with row cap and statement timeout enforced.

        Raises:
            QueryTimeoutError: statement_timeout exceeded.
            SQLExecutionError: any other DB-level failure.
        """
        limited_sql = _apply_limit(sql, self._settings.sql_row_limit)
        start = time.monotonic()

        try:
            async with await psycopg.AsyncConnection.connect(
                **self._connect_kwargs()
            ) as conn:
                async with conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
                    await cur.execute(limited_sql)
                    rows: list[dict[str, Any]] = await cur.fetchall()
        except psycopg.errors.QueryCanceled as exc:
            raise QueryTimeoutError(self._settings.sql_statement_timeout_ms) from exc
        except psycopg.DatabaseError as exc:
            raise SQLExecutionError(str(exc)) from exc

        elapsed = round(time.monotonic() - start, 3)
        logger.info(
            "query executed",
            extra={"row_count": len(rows), "elapsed_s": elapsed},
        )
        return QueryResult(
            rows=rows,
            row_count=len(rows),
            elapsed_s=elapsed,
            sql=limited_sql,
        )
