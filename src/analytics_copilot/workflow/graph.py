from __future__ import annotations

import pathlib
from typing import Any

from langchain_core.language_models.chat_models import BaseChatModel
from langgraph.graph import END, START, StateGraph

from analytics_copilot.core.config import get_settings
from analytics_copilot.services.llm import get_llm
from analytics_copilot.services.manifest_parser import ManifestParser
from analytics_copilot.services.sql_executor import SQLExecutor
from analytics_copilot.services.sql_validator import SQLValidator
from analytics_copilot.workflow.nodes import (
    ErrorHandlerNode,
    ResultFormatterNode,
    SQLExecutorNode,
    SQLGeneratorNode,
    SQLValidatorNode,
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


def build_graph(
    manifest: ManifestParser | None = None,
    executor: SQLExecutor | None = None,
    llm: BaseChatModel | None = None,
    prompts_dir: pathlib.Path | None = None,
) -> Any:
    settings = get_settings()
    resolved_manifest = manifest or ManifestParser(settings.dbt_manifest_path)
    resolved_executor = executor or SQLExecutor(settings)
    validator = SQLValidator(resolved_manifest)
    resolved_prompts_dir = prompts_dir or settings.prompts_dir

    resolved_llm: BaseChatModel = llm or get_llm()

    builder = StateGraph(WorkflowState)

    builder.add_node(
        "sql_generator",
        SQLGeneratorNode(
            manifest=resolved_manifest,
            llm=resolved_llm,
            prompts_dir=resolved_prompts_dir,
        ),
    )
    builder.add_node("sql_validator", SQLValidatorNode(validator))
    builder.add_node("sql_executor", SQLExecutorNode(resolved_executor))
    builder.add_node(
        "result_formatter",
        ResultFormatterNode(llm=resolved_llm, prompts_dir=resolved_prompts_dir),
    )
    builder.add_node("error_handler", ErrorHandlerNode())

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
