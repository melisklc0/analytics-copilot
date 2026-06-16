from __future__ import annotations

from typing import Any

from analytics_copilot.workflow.state import WorkflowState


async def sql_executor_node(state: WorkflowState) -> dict[str, Any]:
    return {"query_result": None}
