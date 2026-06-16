from __future__ import annotations

import logging
from typing import cast

import sqlglot
import sqlglot.expressions as exp

from analytics_copilot.core.exceptions import SQLValidationError
from analytics_copilot.services.manifest_parser import ManifestParser
from analytics_copilot.services.models import MartModel, ValidationResult

logger = logging.getLogger(__name__)

_FORBIDDEN_EXPRESSIONS: tuple[type[exp.Expression], ...] = (
    exp.Group,
    exp.Join,
    exp.Sum,
    exp.Count,
    exp.Avg,
)


class SQLValidator:
    """Validates LLM-generated SQL before execution.

    Three layers:
    1. Write-operation guard — only SELECT is permitted.
    2. Aggregation guard — GROUP BY / SUM / COUNT / AVG / JOIN are rejected.
    3. Table & column check — referenced tables and columns must exist in the manifest.
    """

    def __init__(self, manifest: ManifestParser) -> None:
        self._manifest = manifest

    def validate(self, sql: str) -> ValidationResult:
        try:
            tree = cast(exp.Expression, sqlglot.parse_one(sql, dialect="postgres"))
        except sqlglot.errors.ParseError as exc:
            return ValidationResult(valid=False, error=f"Invalid SQL syntax: {exc}")

        try:
            select = self._check_write_guard(tree)
            self._check_aggregation_guard(select)
            models = self._resolve_tables(select)
            self._check_columns(select, models)
        except SQLValidationError as exc:
            logger.warning("sql validation failed", extra={"error": str(exc)})
            return ValidationResult(valid=False, error=str(exc))

        logger.info("sql validated")
        return ValidationResult(valid=True)

    def _check_write_guard(self, tree: exp.Expression) -> exp.Select:
        if not isinstance(tree, exp.Select):
            raise SQLValidationError(
                f"{type(tree).__name__.upper()} action is not permitted."
            )
        return tree

    def _check_aggregation_guard(self, tree: exp.Select) -> None:
        for node_type in _FORBIDDEN_EXPRESSIONS:
            if tree.find(node_type):
                raise SQLValidationError(
                    f"{node_type.__name__.upper()} is not permitted."
                )

    def _resolve_tables(self, tree: exp.Select) -> list[MartModel]:
        models_by_name = self._manifest.models
        models_by_relation = {m.relation: m for m in models_by_name.values()}
        models: list[MartModel] = []

        for table in tree.find_all(exp.Table):
            if not table.name:
                continue
            table_ref = f"{table.db}.{table.name}" if table.db else table.name
            model = models_by_name.get(table.name) or models_by_relation.get(table_ref)
            if model is None:
                available = ", ".join(sorted(models_by_relation))
                raise SQLValidationError(
                    f"Table '{table_ref}' is not a known AI mart model. "
                    f"Available tables: {available}."
                )
            models.append(model)

        return models

    def _check_columns(self, tree: exp.Select, models: list[MartModel]) -> None:
        if any(isinstance(s, exp.Star) for s in tree.selects) or not models:
            return

        valid_columns = {col.name for model in models for col in model.columns}
        unknown = sorted(
            {
                col.name.lower()
                for col in tree.find_all(exp.Column)
                if col.name.lower() not in valid_columns
            }
        )

        if unknown:
            raise SQLValidationError(
                f"Unknown column(s): {', '.join(unknown)}. "
                f"Valid columns: {', '.join(sorted(valid_columns))}."
            )
