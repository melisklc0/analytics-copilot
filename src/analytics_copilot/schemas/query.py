from __future__ import annotations

from typing import Any

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
