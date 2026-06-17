from __future__ import annotations

import logging
from typing import Any

from analytics_copilot.services.sql_validator import SQLValidator
from analytics_copilot.workflow.state import WorkflowState

log = logging.getLogger(__name__)


class SQLValidatorNode:
    def __init__(self, validator: SQLValidator) -> None:
        self._validator = validator

    async def __call__(self, state: WorkflowState) -> dict[str, Any]:
        sql = state["sql"]
        if not sql:
            log.warning("sql validator called with no sql")
            return {
                "validation_status": "invalid",
                "validation_error": state["error"] or "No SQL was generated.",
            }
        result = self._validator.validate(sql)
        if not result.valid:
            log.warning(
                "sql validation failed",
                extra={
                    "validation_error": result.error,
                    "retry_count": state["retry_count"],
                },
            )
        return {
            "validation_status": "valid" if result.valid else "invalid",
            "validation_error": result.error if not result.valid else None,
        }
