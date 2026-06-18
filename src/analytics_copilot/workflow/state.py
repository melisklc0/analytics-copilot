from __future__ import annotations

from typing import Literal, TypedDict

from analytics_copilot.services.models import QueryResult


class WorkflowState(TypedDict):
    question: str
    mart_context: str | None
    sql: str | None
    sql_rationale: str | None
    validation_status: Literal["valid", "invalid"] | None
    validation_error: str | None
    query_result: QueryResult | None
    retry_count: int
    error: str | None
    response: dict[str, object] | None
