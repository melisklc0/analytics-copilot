from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class ColumnMeta:
    name: str
    description: str
    data_type: str
    filterable: bool


@dataclass
class ModelMeta:
    name: str
    relation: str  # schema.table — ready to use in SQL
    description: str
    columns: list[ColumnMeta] = field(default_factory=list)


def _parse_relation(relation_name: str) -> str:
    """Extract schema.table from a fully-qualified dbt relation name.

    Input:  '"analytics_copilot"."main_marts"."mart_customers"'
    Output: 'main_marts.mart_customers'
    """
    parts = re.findall(r'"([^"]+)"', relation_name)
    if len(parts) >= 2:
        return f"{parts[-2]}.{parts[-1]}"
    return relation_name


class ManifestParser:
    """Loads dbt manifest.json and exposes AI-mart models with LLM-ready context."""

    _AI_TAGS: frozenset[str] = frozenset({"ai", "mart"})

    def __init__(self, manifest_path: Path) -> None:
        self._path = manifest_path
        self._models: dict[str, ModelMeta] | None = None

    def _load(self) -> dict[str, ModelMeta]:
        logger.debug("loading manifest", extra={"path": str(self._path)})

        with open(self._path, encoding="utf-8") as fh:
            raw = json.load(fh)

        result: dict[str, ModelMeta] = {}
        nodes = raw.get("nodes", {})
        if not isinstance(nodes, dict):
            logger.warning(
                "manifest 'nodes' key is missing or not a dict — no models loaded"
            )
            return result

        skipped = 0
        for node in nodes.values():
            if not isinstance(node, dict):
                skipped += 1
                continue
            if node.get("resource_type") != "model":
                continue
            tags = node.get("tags", [])
            if not self._AI_TAGS.issubset(tags):
                skipped += 1
                logger.debug(
                    "skipping node: missing ai/mart tags",
                    extra={"node_name": node.get("name"), "tags": tags},
                )
                continue

            columns: list[ColumnMeta] = []
            for col in node.get("columns", {}).values():
                if not isinstance(col, dict):
                    continue
                meta = col.get("meta") or {}
                columns.append(
                    ColumnMeta(
                        name=str(col.get("name", "")),
                        description=str(col.get("description", "")),
                        data_type=str(col.get("data_type", "") or "text"),
                        filterable=bool(meta.get("filterable", False)),
                    )
                )

            name = str(node.get("name", ""))
            relation_name = str(node.get("relation_name", ""))
            result[name] = ModelMeta(
                name=name,
                relation=_parse_relation(relation_name) if relation_name else name,
                description=str(node.get("description", "")).strip(),
                columns=columns,
            )

        if not result:
            logger.warning(
                "no AI mart models found in manifest — every query will fail; "
                "run `dbt docs generate` and verify models have tags: [ai, mart]",
                extra={"path": str(self._path), "nodes_skipped": skipped},
            )
        else:
            logger.info(
                "manifest loaded",
                extra={"models": list(result.keys()), "skipped": skipped},
            )

        return result

    @property
    def models(self) -> dict[str, ModelMeta]:
        if self._models is None:
            self._models = self._load()
        return self._models

    def get_all_models(self) -> list[ModelMeta]:
        """Return all AI-mart models — used by Schema Selector for relevance ranking."""
        return list(self.models.values())

    def get_summary(self) -> str:
        """Compact model list for the Schema Selector prompt.

        Returns one bullet per model with name and purpose description only.
        No column detail — keeps the selection step context-efficient.
        """
        lines = [
            "Available tables (use these names to select relevant models):",
            "",
        ]
        for model in self.models.values():
            lines.append(
                f"- **{model.name}** (`{model.relation}`): {model.description}"
            )
        return "\n".join(lines)

    def get_context(self, model_names: list[str]) -> str:
        """Format selected models as Markdown context for the SQL Generator prompt.

        Each model renders as a heading + description + column table with type
        and [filterable] hints. Unknown model names are logged as warnings.
        """
        blocks: list[str] = []
        for name in model_names:
            model = self.models.get(name)
            if not model:
                logger.warning("model not found in manifest", extra={"model": name})
                continue
            lines = [
                f"## {model.name}",
                f"**Table:** `{model.relation}`",
                "",
                model.description,
                "",
                "| column | type | description |",
                "|---|---|---|",
            ]
            for col in model.columns:
                hint = " `[filterable]`" if col.filterable else ""
                desc = col.description.replace("|", "\\|")
                lines.append(
                    f"| `{col.name}` | `{col.data_type.upper()}` | {desc}{hint} |"
                )
            blocks.append("\n".join(lines))
        return "\n\n---\n\n".join(blocks)
