import json
from pathlib import Path

import pytest

from analytics_copilot.services.manifest_parser import ManifestParser
from analytics_copilot.services.models import MartModel


FIXTURE_PATH = Path(__file__).parent.parent.parent / "fixtures" / "manifest_sample.json"


@pytest.fixture()
def parser() -> ManifestParser:
    return ManifestParser(FIXTURE_PATH)


class TestManifestLoading:
    def test_loads_only_ai_mart_models(self, parser: ManifestParser) -> None:
        names = {m.name for m in parser.get_all_models()}
        assert names == {"mart_customers", "mart_orders"}

    def test_excludes_staging_models(self, parser: ManifestParser) -> None:
        names = {m.name for m in parser.get_all_models()}
        assert "stg__customers" not in names

    def test_excludes_source_nodes(self, parser: ManifestParser) -> None:
        # sources live under "sources" key, not "nodes" — must not appear
        names = {m.name for m in parser.get_all_models()}
        assert "orders" not in names

    def test_relation_strips_database_prefix(self, parser: ManifestParser) -> None:
        customers = parser.models["mart_customers"]
        assert customers.relation == "main_marts.mart_customers"

    def test_columns_loaded(self, parser: ManifestParser) -> None:
        customers = parser.models["mart_customers"]
        col_names = {c.name for c in customers.columns}
        assert {
            "customer_id",
            "customer_state",
            "customer_segment",
            "total_orders",
            "total_revenue",
        } == col_names

    def test_filterable_flag_parsed(self, parser: ManifestParser) -> None:
        customers = parser.models["mart_customers"]
        by_name = {c.name: c for c in customers.columns}
        assert by_name["customer_state"].filterable is True
        assert by_name["customer_id"].filterable is False

    def test_data_type_parsed(self, parser: ManifestParser) -> None:
        orders = parser.models["mart_orders"]
        by_name = {c.name: c for c in orders.columns}
        assert by_name["order_id"].data_type == "text"
        assert by_name["order_year"].data_type == "integer"
        assert by_name["total_revenue"].data_type == "numeric"

    def test_missing_data_type_defaults_to_text(self, tmp_path: Path) -> None:
        manifest = {
            "nodes": {
                "model.proj.mart_x": {
                    "resource_type": "model",
                    "name": "mart_x",
                    "description": "test",
                    "tags": ["ai", "mart"],
                    "relation_name": '"db"."schema"."mart_x"',
                    "columns": {
                        "col_a": {"name": "col_a", "description": "no type", "meta": {}}
                    },
                }
            }
        }
        p = tmp_path / "manifest.json"
        p.write_text(json.dumps(manifest))
        m = ManifestParser(p).models["mart_x"]
        assert m.columns[0].data_type == "text"

    def test_raises_on_missing_file(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError):
            ManifestParser(tmp_path / "nonexistent.json").models  # noqa: B018


class TestGetAllModels:
    def test_returns_list_of_model_meta(self, parser: ManifestParser) -> None:
        models = parser.get_all_models()
        assert all(isinstance(m, MartModel) for m in models)

    def test_returns_correct_count(self, parser: ManifestParser) -> None:
        assert len(parser.get_all_models()) == 2


class TestGetSummary:
    def test_contains_all_model_names(self, parser: ManifestParser) -> None:
        summary = parser.get_summary()
        assert "mart_customers" in summary
        assert "mart_orders" in summary

    def test_contains_relation(self, parser: ManifestParser) -> None:
        summary = parser.get_summary()
        assert "main_marts.mart_customers" in summary

    def test_contains_description(self, parser: ManifestParser) -> None:
        summary = parser.get_summary()
        assert "customer lifecycle" in summary.lower()

    def test_no_column_detail(self, parser: ManifestParser) -> None:
        summary = parser.get_summary()
        assert "| column |" not in summary
        assert "customer_state" not in summary

    def test_returns_string(self, parser: ManifestParser) -> None:
        assert isinstance(parser.get_summary(), str)


class TestGetContext:
    def test_includes_table_name(self, parser: ManifestParser) -> None:
        ctx = parser.get_context(["mart_customers"])
        assert "main_marts.mart_customers" in ctx

    def test_includes_description(self, parser: ManifestParser) -> None:
        ctx = parser.get_context(["mart_customers"])
        assert "customer lifecycle" in ctx.lower()

    def test_includes_column_names(self, parser: ManifestParser) -> None:
        ctx = parser.get_context(["mart_customers"])
        assert "customer_state" in ctx
        assert "customer_segment" in ctx

    def test_filterable_hint_present(self, parser: ManifestParser) -> None:
        ctx = parser.get_context(["mart_customers"])
        assert "[filterable]" in ctx

    def test_data_type_uppercased_in_context(self, parser: ManifestParser) -> None:
        ctx = parser.get_context(["mart_orders"])
        assert "INTEGER" in ctx
        assert "NUMERIC" in ctx

    def test_multiple_models_separated_by_divider(self, parser: ManifestParser) -> None:
        ctx = parser.get_context(["mart_customers", "mart_orders"])
        assert "---" in ctx
        assert "main_marts.mart_customers" in ctx
        assert "main_marts.mart_orders" in ctx

    def test_unknown_model_name_skipped(self, parser: ManifestParser) -> None:
        ctx = parser.get_context(["does_not_exist"])
        assert ctx == ""

    def test_mixed_known_and_unknown_skips_gracefully(
        self, parser: ManifestParser
    ) -> None:
        ctx = parser.get_context(["mart_customers", "does_not_exist"])
        assert "main_marts.mart_customers" in ctx
        assert "does_not_exist" not in ctx

    def test_empty_list_returns_empty_string(self, parser: ManifestParser) -> None:
        assert parser.get_context([]) == ""
