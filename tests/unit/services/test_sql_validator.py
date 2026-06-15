from unittest.mock import MagicMock

import pytest

from analytics_copilot.services.manifest_parser import ManifestParser
from analytics_copilot.services.models import MartColumn, MartModel
from analytics_copilot.services.models import ValidationResult
from analytics_copilot.services.sql_validator import SQLValidator


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_manifest(models: list[MartModel]) -> ManifestParser:
    mock = MagicMock(spec=ManifestParser)
    mock.models = {m.name: m for m in models}
    mock.get_all_models.return_value = models
    return mock  # type: ignore[return-value]


CUSTOMERS_MODEL = MartModel(
    name="mart_customers",
    relation="main_marts.mart_customers",
    description="Customer lifecycle metrics",
    columns=[
        MartColumn(
            name="customer_id", description="", data_type="text", filterable=False
        ),
        MartColumn(
            name="customer_state", description="", data_type="text", filterable=True
        ),
        MartColumn(
            name="total_revenue", description="", data_type="numeric", filterable=False
        ),
        MartColumn(
            name="total_orders", description="", data_type="integer", filterable=False
        ),
    ],
)

ORDERS_MODEL = MartModel(
    name="mart_orders",
    relation="main_marts.mart_orders",
    description="Order details",
    columns=[
        MartColumn(name="order_id", description="", data_type="text", filterable=False),
        MartColumn(
            name="order_status", description="", data_type="text", filterable=True
        ),
        MartColumn(
            name="total_revenue", description="", data_type="numeric", filterable=False
        ),
    ],
)


@pytest.fixture()
def manifest() -> ManifestParser:
    return _make_manifest([CUSTOMERS_MODEL, ORDERS_MODEL])


@pytest.fixture()
def validator(manifest: ManifestParser) -> SQLValidator:
    return SQLValidator(manifest)


# ---------------------------------------------------------------------------
# Write guard
# ---------------------------------------------------------------------------


class TestWriteGuard:
    @pytest.mark.parametrize(
        "sql",
        [
            "INSERT INTO mart_customers VALUES (1)",
            "UPDATE mart_customers SET x = 1",
            "DELETE FROM mart_customers",
            "DROP TABLE mart_customers",
            "CREATE TABLE foo (id INT)",
            "ALTER TABLE mart_customers ADD COLUMN x INT",
            "TRUNCATE mart_customers",
        ],
    )
    def test_rejects_write_operations(self, validator: SQLValidator, sql: str) -> None:
        result = validator.validate(sql)
        assert result.valid is False
        assert result.error is not None

    def test_error_mentions_delete_keyword(self, validator: SQLValidator) -> None:
        result = validator.validate("DELETE FROM mart_customers")
        assert "DELETE" in (result.error or "")

    def test_error_mentions_insert_keyword(self, validator: SQLValidator) -> None:
        result = validator.validate("INSERT INTO mart_customers VALUES (1)")
        assert "INSERT" in (result.error or "")


# ---------------------------------------------------------------------------
# Aggregation guard
# ---------------------------------------------------------------------------


class TestAggregationGuard:
    @pytest.mark.parametrize(
        "sql",
        [
            "SELECT customer_state, SUM(total_revenue) FROM mart_customers GROUP BY 1",
            "SELECT COUNT(*) FROM mart_customers",
            "SELECT AVG(total_revenue) FROM mart_customers",
            "SELECT * FROM mart_customers JOIN mart_orders ON mart_customers.customer_id = mart_orders.order_id",
        ],
    )
    def test_rejects_aggregation(self, validator: SQLValidator, sql: str) -> None:
        result = validator.validate(sql)
        assert result.valid is False

    def test_error_mentions_sum(self, validator: SQLValidator) -> None:
        result = validator.validate("SELECT SUM(total_revenue) FROM mart_customers")
        assert "SUM" in (result.error or "")

    def test_error_mentions_group_by(self, validator: SQLValidator) -> None:
        result = validator.validate(
            "SELECT customer_state FROM mart_customers GROUP BY customer_state"
        )
        assert "GROUP BY" in (result.error or "")

    def test_column_named_join_date_is_not_rejected(
        self, validator: SQLValidator
    ) -> None:
        """sqlglot parses AST nodes — column names containing keywords are safe."""
        manifest = _make_manifest(
            [
                MartModel(
                    name="mart_orders",
                    relation="main_marts.mart_orders",
                    description="",
                    columns=[
                        MartColumn(
                            name="join_date",
                            description="",
                            data_type="date",
                            filterable=False,
                        )
                    ],
                )
            ]
        )
        v = SQLValidator(manifest)
        result = v.validate("SELECT join_date FROM mart_orders")
        assert result.valid is True

    def test_string_literal_with_count_is_not_rejected(
        self, validator: SQLValidator
    ) -> None:
        """sqlglot parses AST nodes — COUNT in a string literal is safe."""
        result = validator.validate(
            "SELECT customer_id FROM mart_customers WHERE customer_state = 'use COUNT'"
        )
        assert result.valid is True


# ---------------------------------------------------------------------------
# SELECT requirement
# ---------------------------------------------------------------------------


class TestSelectRequirement:
    def test_rejects_explain(self, validator: SQLValidator) -> None:
        result = validator.validate("EXPLAIN SELECT * FROM mart_customers")
        assert result.valid is False

    def test_accepts_select_with_leading_whitespace(
        self, validator: SQLValidator
    ) -> None:
        result = validator.validate("  SELECT * FROM mart_customers")
        assert result.valid is True


# ---------------------------------------------------------------------------
# Table reference check
# ---------------------------------------------------------------------------


class TestTableCheck:
    def test_accepts_known_table_by_name(self, validator: SQLValidator) -> None:
        result = validator.validate("SELECT * FROM mart_customers")
        assert result.valid is True

    def test_accepts_known_table_by_relation(self, validator: SQLValidator) -> None:
        result = validator.validate("SELECT * FROM main_marts.mart_customers")
        assert result.valid is True

    def test_rejects_unknown_table(self, validator: SQLValidator) -> None:
        result = validator.validate("SELECT * FROM raw.orders")
        assert result.valid is False
        assert "raw.orders" in (result.error or "")

    def test_error_lists_available_tables(self, validator: SQLValidator) -> None:
        result = validator.validate("SELECT * FROM unknown_table")
        assert "main_marts.mart_customers" in (result.error or "")


# ---------------------------------------------------------------------------
# Column check
# ---------------------------------------------------------------------------


class TestColumnCheck:
    def test_accepts_valid_columns(self, validator: SQLValidator) -> None:
        result = validator.validate(
            "SELECT customer_id, total_revenue FROM mart_customers LIMIT 10"
        )
        assert result.valid is True

    def test_accepts_wildcard(self, validator: SQLValidator) -> None:
        result = validator.validate("SELECT * FROM mart_customers")
        assert result.valid is True

    def test_rejects_unknown_column(self, validator: SQLValidator) -> None:
        result = validator.validate(
            "SELECT customer_id, nonexistent_col FROM mart_customers"
        )
        assert result.valid is False
        assert "nonexistent_col" in (result.error or "")

    def test_accepts_column_with_alias(self, validator: SQLValidator) -> None:
        result = validator.validate(
            "SELECT customer_id AS cid, total_revenue AS rev FROM mart_customers"
        )
        assert result.valid is True

    def test_accepts_table_prefixed_column(self, validator: SQLValidator) -> None:
        result = validator.validate(
            "SELECT mc.customer_id, mc.total_revenue FROM mart_customers AS mc"
        )
        assert result.valid is True

    def test_rejects_unknown_column_in_where(self, validator: SQLValidator) -> None:
        result = validator.validate(
            "SELECT customer_id FROM mart_customers WHERE ghost_col = 'x'"
        )
        assert result.valid is False
        assert "ghost_col" in (result.error or "")

    def test_accepts_columns_across_models(self, validator: SQLValidator) -> None:
        result = validator.validate("SELECT total_revenue FROM mart_orders LIMIT 5")
        assert result.valid is True

    def test_error_lists_valid_columns(self, validator: SQLValidator) -> None:
        result = validator.validate("SELECT bad_col FROM mart_customers")
        assert "customer_id" in (result.error or "")


# ---------------------------------------------------------------------------
# ValidationResult dataclass
# ---------------------------------------------------------------------------


class TestValidationResult:
    def test_valid_result_has_no_error(self) -> None:
        r = ValidationResult(valid=True)
        assert r.error is None

    def test_invalid_result_carries_message(self) -> None:
        r = ValidationResult(valid=False, error="bad sql")
        assert r.error == "bad sql"
