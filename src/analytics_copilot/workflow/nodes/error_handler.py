from __future__ import annotations

from typing import Any

from analytics_copilot.workflow.state import WorkflowState


class ErrorHandlerNode:
    async def __call__(self, state: WorkflowState) -> dict[str, Any]:
        return {
            "response": {
                "answer": state["error"]
                or "An error occurred. Please try rephrasing your question.",
                "sql": state["sql"] or "",
                "rows": [],
                "row_count": 0,
            }
        }
