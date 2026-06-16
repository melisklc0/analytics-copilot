from __future__ import annotations

from typing import Any

from analytics_copilot.workflow.state import WorkflowState


class ResultFormatterNode:
    async def __call__(self, state: WorkflowState) -> dict[str, Any]:
        return {
            "response": {
                "answer": "",
                "sql": state["sql"] or "",
                "rows": [],
                "row_count": 0,
            }
        }
