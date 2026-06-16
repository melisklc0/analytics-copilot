from __future__ import annotations

from typing import Any

from analytics_copilot.workflow.state import WorkflowState


async def sql_validator_node(state: WorkflowState) -> dict[str, Any]:
    return {"validation_status": "valid", "validation_error": None}
