import asyncio
import pathlib
from typing import Any
from unittest.mock import MagicMock

import pytest
import yaml
from langchain_core.runnables import RunnableLambda

from analytics_copilot.workflow.models import SQLOutput
from analytics_copilot.workflow.nodes.sql_generator import SQLGeneratorNode


@pytest.fixture
def prompts_dir(tmp_path: pathlib.Path) -> pathlib.Path:
    (tmp_path / "sql_generator.yaml").write_text(
        yaml.dump(
            {
                "system": "Generate SQL.",
                "user": "{mart_context}\n{question}{retry_note}",
            }
        )
    )
    return tmp_path


@pytest.fixture
def mock_manifest() -> MagicMock:
    manifest = MagicMock()
    manifest.get_all_models.return_value = []
    manifest.get_context.return_value = "## mart_customers\n| column | type |"
    return manifest


def _make_node(
    mock_manifest: MagicMock,
    prompts_dir: pathlib.Path,
    sql: str = "SELECT customer_id FROM mart.mart_customers LIMIT 10",
    side_effect: Exception | None = None,
) -> tuple[SQLGeneratorNode, list[Any]]:
    """Returns the node and a list of captured prompt values passed to the LLM."""
    captured: list[Any] = []

    async def fake_llm(prompt_value: Any) -> SQLOutput:
        captured.append(prompt_value)
        if side_effect is not None:
            raise side_effect
        return SQLOutput(sql=sql)

    mock_chain = RunnableLambda(fake_llm)
    mock_llm = MagicMock()
    mock_llm.with_structured_output = MagicMock(return_value=mock_chain)
    node = SQLGeneratorNode(
        manifest=mock_manifest, llm=mock_llm, prompts_dir=prompts_dir
    )
    return node, captured


def _base_state(**overrides: Any) -> dict[str, Any]:
    state: dict[str, Any] = {
        "question": "What are the top 10 customers?",
        "mart_context": None,
        "sql": None,
        "validation_status": None,
        "validation_error": None,
        "query_result": None,
        "retry_count": 0,
        "error": None,
        "response": None,
    }
    state.update(overrides)
    return state


def test_generates_sql_from_question(
    mock_manifest: MagicMock, prompts_dir: pathlib.Path
) -> None:
    expected = "SELECT customer_id FROM mart.mart_customers LIMIT 10"
    node, _ = _make_node(mock_manifest, prompts_dir, sql=expected)
    result = asyncio.run(node(_base_state()))
    assert result["sql"] == expected
    assert result.get("error") is None


def test_no_retry_count_increment_on_first_call(
    mock_manifest: MagicMock, prompts_dir: pathlib.Path
) -> None:
    node, _ = _make_node(mock_manifest, prompts_dir)
    result = asyncio.run(node(_base_state()))
    assert "retry_count" not in result


def test_increments_retry_count_on_validation_error(
    mock_manifest: MagicMock, prompts_dir: pathlib.Path
) -> None:
    node, _ = _make_node(mock_manifest, prompts_dir)
    state = _base_state(
        validation_error="Table 'foo' is not a known AI mart model.",
        retry_count=0,
    )
    result = asyncio.run(node(state))
    assert result["retry_count"] == 1


def test_retry_note_included_in_prompt_on_validation_error(
    mock_manifest: MagicMock, prompts_dir: pathlib.Path
) -> None:
    error_msg = "Table 'foo' is not a known AI mart model."
    node, captured = _make_node(mock_manifest, prompts_dir)
    asyncio.run(node(_base_state(validation_error=error_msg)))
    assert len(captured) == 1
    assert error_msg in str(captured[0])


def test_no_retry_note_when_no_validation_error(
    mock_manifest: MagicMock, prompts_dir: pathlib.Path
) -> None:
    node, captured = _make_node(mock_manifest, prompts_dir)
    asyncio.run(node(_base_state()))
    assert len(captured) == 1
    assert "Previous SQL was rejected" not in str(captured[0])


def test_sets_error_on_llm_exception(
    mock_manifest: MagicMock, prompts_dir: pathlib.Path
) -> None:
    node, _ = _make_node(
        mock_manifest,
        prompts_dir,
        side_effect=Exception("API connection error"),
    )
    result = asyncio.run(node(_base_state()))
    assert result["sql"] is None
    assert "API connection error" in result["error"]


def test_reuses_mart_context_from_state(
    mock_manifest: MagicMock, prompts_dir: pathlib.Path
) -> None:
    node, _ = _make_node(mock_manifest, prompts_dir)
    cached_context = "## cached mart context"
    result = asyncio.run(node(_base_state(mart_context=cached_context)))
    assert result["mart_context"] == cached_context
    mock_manifest.get_context.assert_not_called()


def test_builds_mart_context_from_manifest_when_none(
    mock_manifest: MagicMock, prompts_dir: pathlib.Path
) -> None:
    node, _ = _make_node(mock_manifest, prompts_dir)
    result = asyncio.run(node(_base_state()))
    assert result["mart_context"] is not None
    mock_manifest.get_all_models.assert_called_once()
    mock_manifest.get_context.assert_called_once()
