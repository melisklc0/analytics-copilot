from __future__ import annotations

from typing import Any

from analytics_copilot.workflow.state import WorkflowState


async def result_formatter_node(state: WorkflowState) -> dict[str, Any]:
    return {
        "response": {
            "answer": "",
            "sql": state["sql"] or "",
            "rows": [],
            "row_count": 0,
        }
    }
