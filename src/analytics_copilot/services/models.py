from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class MartColumn:
    name: str
    description: str
    data_type: str
    filterable: bool


@dataclass
class MartModel:
    name: str
    relation: str  # schema.table — ready to use in SQL
    description: str
    columns: list[MartColumn] = field(default_factory=list)


@dataclass
class ValidationResult:
    valid: bool
    error: str | None = None


@dataclass
class QueryResult:
    rows: list[dict[str, Any]]
    row_count: int
    elapsed_s: float
    sql: str
