from __future__ import annotations

import sqlglot
import sqlglot.expressions as exp

from analytics_copilot.services.manifest_parser import ManifestParser
from analytics_copilot.services.models import MartModel, ValidationResult

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
            tree = sqlglot.parse_one(sql, dialect="postgres")
        except sqlglot.errors.ParseError as exc:
            return ValidationResult(valid=False, error=f"Invalid SQL syntax: {exc}")

        if not isinstance(tree, exp.Select):
            stmt = type(tree).__name__.upper()
            return ValidationResult(
                valid=False,
                error=f"{stmt} action is not permitted.",
            )

        for node_type in _FORBIDDEN_EXPRESSIONS:
            if tree.find(node_type):
                return ValidationResult(
                    valid=False, error=f"{node_type.__name__.upper()} is not permitted."
                )

        table_error = self._check_tables(tree)
        if table_error:
            return ValidationResult(valid=False, error=table_error)

        column_error = self._check_columns(tree)
        if column_error:
            return ValidationResult(valid=False, error=column_error)

        return ValidationResult(valid=True)

    def _check_tables(self, tree: exp.Select) -> str | None:
        valid_names = set(self._manifest.models.keys())
        valid_relations = {m.relation for m in self._manifest.get_all_models()}

        for table in tree.find_all(exp.Table):
            if not table.name:
                continue
            qualified = f"{table.db}.{table.name}" if table.db else table.name
            if table.name not in valid_names and qualified not in valid_relations:
                return (
                    f"Table '{qualified}' is not a known AI mart model. "
                    f"Available tables: {', '.join(sorted(valid_relations))}."
                )
        return None

    def _check_columns(self, tree: exp.Select) -> str | None:
        if any(isinstance(s, exp.Star) for s in tree.selects):
            return None

        models = self._resolve_models(tree)
        if not models:
            return None

        valid_columns = {col.name for model in models for col in model.columns}
        unknown = sorted(
            {
                col.name.lower()
                for col in tree.find_all(exp.Column)
                if col.name.lower() not in valid_columns
            }
        )

        if unknown:
            return (
                f"Unknown column(s): {', '.join(unknown)}. "
                f"Valid columns for the selected model(s): {', '.join(sorted(valid_columns))}."
            )
        return None

    def _resolve_models(self, tree: exp.Select) -> list[MartModel]:
        by_name = self._manifest.models
        by_relation = {m.relation: m for m in self._manifest.get_all_models()}
        models: list[MartModel] = []
        for table in tree.find_all(exp.Table):
            if not table.name:
                continue
            qualified = f"{table.db}.{table.name}" if table.db else table.name
            model = by_name.get(table.name) or by_relation.get(qualified)
            if model:
                models.append(model)
        return models
