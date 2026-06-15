from __future__ import annotations

import logging
import re
import time
from typing import Any

import psycopg
import psycopg.rows

from analytics_copilot.core.config import Settings, get_settings
from analytics_copilot.core.exceptions import QueryTimeoutError, SQLExecutionError
from analytics_copilot.services.models import QueryResult

logger = logging.getLogger(__name__)


def _apply_limit(sql: str, max_rows: int) -> str:
    """Enforce a maximum row cap. Replaces existing LIMIT if it exceeds max_rows."""
    stripped = sql.rstrip().rstrip(";")
    m = re.search(r"\bLIMIT\s+(\d+)\b", stripped, re.IGNORECASE)
    if m:
        if int(m.group(1)) > max_rows:
            return re.sub(
                r"\bLIMIT\s+\d+\b",
                f"LIMIT {max_rows}",
                stripped,
                flags=re.IGNORECASE,
            )
        return stripped
    return f"{stripped}\nLIMIT {max_rows}"


class SQLExecutor:
    """Async, read-only SQL executor backed by the analyst_ro PostgreSQL role."""

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
            raise QueryTimeoutError(
                self._settings.sql_statement_timeout_ms // 1000
            ) from exc
        except (psycopg.OperationalError, psycopg.ProgrammingError) as exc:
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
