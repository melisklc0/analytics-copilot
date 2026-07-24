from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class QueryRequest(BaseModel):
    question: str = Field(..., min_length=1)


class QueryResponse(BaseModel):
    answer: str
    sql: str | None = None
    rows: list[dict[str, Any]] = []
    row_count: int = 0
    retry_count: int = 0
    error: str | None = None


class TraceEvent(BaseModel):
    """One server-sent event on the /query/stream trace.

    ``node``  — a workflow node finished (sql_generator/sql_validator/...);
                ``data`` is that node's public slice of state.
    ``final`` — the workflow ended; ``data`` holds the QueryResponse fields.
    ``error`` — the stream failed; ``data`` carries a safe message.
    """

    type: Literal["node", "final", "error"]
    node: str | None = None
    data: dict[str, Any] = Field(default_factory=dict)
