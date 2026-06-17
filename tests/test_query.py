from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from analytics_copilot.api.dependencies import get_graph
from analytics_copilot.app import create_app


def _mock_graph(result: dict[str, Any]) -> MagicMock:
    graph = MagicMock()
    graph.ainvoke = AsyncMock(return_value=result)
    return graph


def _success_result(
    sql: str = "SELECT customer_id FROM mart.mart_customers LIMIT 10",
    rows: list[dict[str, Any]] | None = None,
    answer: str = "Here are the top customers.",
) -> dict[str, Any]:
    qr = MagicMock()
    qr.rows = rows or [{"customer_id": "abc123"}]
    qr.row_count = len(qr.rows)
    return {
        "question": "top customers?",
        "mart_context": "",
        "sql": sql,
        "validation_status": "valid",
        "validation_error": None,
        "query_result": qr,
        "retry_count": 0,
        "error": None,
        "response": {"answer": answer},
    }


def _error_result(error: str = "Could not generate SQL.") -> dict[str, Any]:
    return {
        "question": "?",
        "mart_context": None,
        "sql": None,
        "validation_status": "invalid",
        "validation_error": error,
        "query_result": None,
        "retry_count": 2,
        "error": error,
        "response": {"answer": error},
    }


@pytest.fixture
def client() -> TestClient:
    app = create_app()
    app.dependency_overrides[get_graph] = lambda: _mock_graph(_success_result())
    return TestClient(app)


def test_query_returns_200_with_sql_and_rows(client: TestClient) -> None:
    response = client.post("/query", json={"question": "Top 10 customers?"})
    assert response.status_code == 200
    data = response.json()
    assert data["sql"] == "SELECT customer_id FROM mart.mart_customers LIMIT 10"
    assert data["row_count"] == 1
    assert data["answer"] == "Here are the top customers."
    assert data["error"] is None


def test_query_response_includes_x_request_id_header(client: TestClient) -> None:
    response = client.post("/query", json={"question": "test?"})
    assert "x-request-id" in response.headers


def test_query_forwards_x_request_id_from_caller(client: TestClient) -> None:
    custom_id = "my-trace-123"
    response = client.post(
        "/query", json={"question": "test?"}, headers={"X-Request-ID": custom_id}
    )
    assert response.headers["x-request-id"] == custom_id


def test_query_workflow_error_returns_200_with_error_field() -> None:
    app = create_app()
    app.dependency_overrides[get_graph] = lambda: _mock_graph(
        _error_result("Could not generate SQL.")
    )
    client = TestClient(app)
    response = client.post("/query", json={"question": "?"})
    assert response.status_code == 200
    assert response.json()["error"] == "Could not generate SQL."


def test_query_empty_question_returns_422() -> None:
    app = create_app()
    app.dependency_overrides[get_graph] = lambda: None
    client = TestClient(app)
    response = client.post("/query", json={"question": ""})
    assert response.status_code == 422


def test_query_retry_count_reflected_in_response() -> None:
    result = _success_result()
    result["retry_count"] = 1
    app = create_app()
    app.dependency_overrides[get_graph] = lambda: _mock_graph(result)
    client = TestClient(app)
    response = client.post("/query", json={"question": "test?"})
    assert response.json()["retry_count"] == 1
