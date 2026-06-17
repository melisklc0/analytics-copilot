from __future__ import annotations

from pydantic import BaseModel


class SQLOutput(BaseModel):
    """Structured output produced by the SQL generator LLM call."""

    sql: str
