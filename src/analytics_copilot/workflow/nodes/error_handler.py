from __future__ import annotations

import logging
from typing import Any

from analytics_copilot.workflow.state import WorkflowState

log = logging.getLogger(__name__)


class ErrorHandlerNode:
    async def __call__(self, state: WorkflowState) -> dict[str, Any]:
        log.error(
            "workflow terminated with error",
            extra={
                "question": state["question"],
                "error": state["error"],
                "sql": state["sql"],
                "retry_count": state["retry_count"],
            },
        )
        return {
            "response": {
                "answer": state["error"]
                or "An error occurred. Please try rephrasing your question.",
                "sql": state["sql"] or "",
                "rows": [],
                "row_count": 0,
            }
        }
