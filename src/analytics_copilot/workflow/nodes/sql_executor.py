from __future__ import annotations

import logging
from typing import Any

from analytics_copilot.core.exceptions import QueryTimeoutError, SQLExecutionError
from analytics_copilot.services.sql_executor import SQLExecutor
from analytics_copilot.workflow.state import WorkflowState

log = logging.getLogger(__name__)


class SQLExecutorNode:
    def __init__(self, executor: SQLExecutor) -> None:
        self._executor = executor

    async def __call__(self, state: WorkflowState) -> dict[str, Any]:
        sql = state["sql"]
        if not sql:
            log.warning("sql executor called with no sql")
            return {"error": "No SQL to execute.", "query_result": None}
        try:
            result = await self._executor.run(sql)
            log.info("sql executed", extra={"row_count": result.row_count})
            return {"query_result": result}
        except QueryTimeoutError as exc:
            log.warning("sql timed out", extra={"sql": sql})
            return {"error": str(exc), "query_result": None}
        except SQLExecutionError as exc:
            log.error("sql execution failed", extra={"sql": sql, "error": str(exc)})
            return {"error": str(exc), "query_result": None}
