from __future__ import annotations

from typing import Any

from langgraph.graph import END, START, StateGraph

from analytics_copilot.workflow.nodes import (
    error_handler_node,
    result_formatter_node,
    sql_executor_node,
    sql_generator_node,
    sql_validator_node,
)
from analytics_copilot.workflow.state import WorkflowState


def _route_after_validator(state: WorkflowState) -> str:
    if state["validation_status"] == "valid":
        return "sql_executor"
    if state["retry_count"] < 2:
        return "sql_generator"
    return "error_handler"


def _route_after_executor(state: WorkflowState) -> str:
    if state["error"]:
        return "error_handler"
    return "result_formatter"


def build_graph() -> Any:
    builder = StateGraph(WorkflowState)

    builder.add_node("sql_generator", sql_generator_node)
    builder.add_node("sql_validator", sql_validator_node)
    builder.add_node("sql_executor", sql_executor_node)
    builder.add_node("result_formatter", result_formatter_node)
    builder.add_node("error_handler", error_handler_node)

    builder.add_edge(START, "sql_generator")
    builder.add_edge("sql_generator", "sql_validator")
    builder.add_conditional_edges(
        "sql_validator",
        _route_after_validator,
        {
            "sql_executor": "sql_executor",
            "sql_generator": "sql_generator",
            "error_handler": "error_handler",
        },
    )
    builder.add_conditional_edges(
        "sql_executor",
        _route_after_executor,
        {"result_formatter": "result_formatter", "error_handler": "error_handler"},
    )
    builder.add_edge("result_formatter", END)
    builder.add_edge("error_handler", END)

    return builder.compile()
