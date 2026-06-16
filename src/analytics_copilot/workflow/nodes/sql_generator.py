from __future__ import annotations

from typing import Any

from analytics_copilot.workflow.state import WorkflowState


class SQLGeneratorNode:
    async def __call__(self, state: WorkflowState) -> dict[str, Any]:
        updates: dict[str, Any] = {}
        if state["validation_error"] is not None:
            updates["retry_count"] = state["retry_count"] + 1
        return {**updates, "sql": None}
