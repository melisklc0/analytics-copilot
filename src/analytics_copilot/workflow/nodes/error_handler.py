from __future__ import annotations

from typing import Any

from analytics_copilot.workflow.state import WorkflowState


async def error_handler_node(state: WorkflowState) -> dict[str, Any]:
    return {
        "response": {
            "answer": state["error"]
            or "An error occurred. Please try rephrasing your question.",
            "sql": state["sql"] or "",
            "rows": [],
            "row_count": 0,
        }
    }
