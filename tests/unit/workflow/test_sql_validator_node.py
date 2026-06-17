import asyncio
from unittest.mock import MagicMock

from analytics_copilot.services.models import ValidationResult
from analytics_copilot.workflow.nodes.sql_validator import SQLValidatorNode
from analytics_copilot.workflow.state import WorkflowState


def _state(**overrides: object) -> WorkflowState:
    base: WorkflowState = {
        "question": "top customers?",
        "mart_context": None,
        "sql": "SELECT * FROM mart_customers",
        "validation_status": None,
        "validation_error": None,
        "query_result": None,
        "retry_count": 0,
        "error": None,
        "response": None,
    }
    return {**base, **overrides}  # type: ignore[return-value]


def _run(coro):  # type: ignore[no-untyped-def]
    return asyncio.run(coro)


class TestSQLValidatorNode:
    def test_valid_sql_returns_valid_status(self) -> None:
        mock_validator = MagicMock()
        mock_validator.validate.return_value = ValidationResult(valid=True)
        node = SQLValidatorNode(mock_validator)

        result = _run(node(_state()))

        assert result["validation_status"] == "valid"
        assert result["validation_error"] is None

    def test_invalid_sql_returns_error_message(self) -> None:
        mock_validator = MagicMock()
        mock_validator.validate.return_value = ValidationResult(
            valid=False, error="JOIN is not permitted."
        )
        node = SQLValidatorNode(mock_validator)

        result = _run(node(_state(sql="SELECT a FROM t1 JOIN t2 ON t1.id = t2.id")))

        assert result["validation_status"] == "invalid"
        assert result["validation_error"] == "JOIN is not permitted."

    def test_none_sql_returns_invalid_without_calling_validator(self) -> None:
        mock_validator = MagicMock()
        node = SQLValidatorNode(mock_validator)

        result = _run(node(_state(sql=None)))

        assert result["validation_status"] == "invalid"
        assert result["validation_error"] == "No SQL was generated."
        mock_validator.validate.assert_not_called()

    def test_none_sql_uses_llm_error_as_validation_error(self) -> None:
        mock_validator = MagicMock()
        node = SQLValidatorNode(mock_validator)
        llm_error = "OpenAI API timeout after 30s"

        result = _run(node(_state(sql=None, error=llm_error)))

        assert result["validation_status"] == "invalid"
        assert result["validation_error"] == llm_error
        mock_validator.validate.assert_not_called()

    def test_empty_sql_returns_invalid_without_calling_validator(self) -> None:
        mock_validator = MagicMock()
        node = SQLValidatorNode(mock_validator)

        result = _run(node(_state(sql="")))

        assert result["validation_status"] == "invalid"
        mock_validator.validate.assert_not_called()

    def test_validator_receives_exact_sql(self) -> None:
        mock_validator = MagicMock()
        mock_validator.validate.return_value = ValidationResult(valid=True)
        node = SQLValidatorNode(mock_validator)
        sql = "SELECT customer_id FROM mart_customers LIMIT 10"

        _run(node(_state(sql=sql)))

        mock_validator.validate.assert_called_once_with(sql)
