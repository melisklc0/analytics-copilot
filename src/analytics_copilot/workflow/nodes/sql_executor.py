from __future__ import annotations

from typing import Any

from analytics_copilot.core.exceptions import QueryTimeoutError, SQLExecutionError
from analytics_copilot.services.sql_executor import SQLExecutor
from analytics_copilot.workflow.state import WorkflowState


class SQLExecutorNode:
    def __init__(self, executor: SQLExecutor) -> None:
        self._executor = executor

    async def __call__(self, state: WorkflowState) -> dict[str, Any]:
        sql = state["sql"]
        if not sql:
            return {"error": "No SQL to execute.", "query_result": None}
        try:
            result = await self._executor.run(sql)
            return {"query_result": result}
        except (QueryTimeoutError, SQLExecutionError) as exc:
            return {"error": str(exc), "query_result": None}
