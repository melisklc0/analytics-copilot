from __future__ import annotations

import json
import logging
import pathlib
from typing import Any

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableConfig

from analytics_copilot.services.prompt_loader import load_prompt
from analytics_copilot.workflow.models import ResultOutput
from analytics_copilot.workflow.state import WorkflowState

log = logging.getLogger(__name__)

_ROWS_PREVIEW_LIMIT = 20


class ResultFormatterNode:
    def __init__(self, llm: BaseChatModel, prompts_dir: pathlib.Path) -> None:
        template = load_prompt(prompts_dir, "result_formatter")
        prompt = ChatPromptTemplate.from_messages(
            [
                ("system", template["system"]),
                ("human", template["user"]),
            ]
        )
        self._chain: Any = prompt | llm.with_structured_output(ResultOutput)

    async def __call__(
        self, state: WorkflowState, config: RunnableConfig
    ) -> dict[str, Any]:
        query_result = state["query_result"]
        if query_result is None:
            return {
                "response": {
                    "answer": "No results were returned.",
                    "sql": state["sql"] or "",
                    "rows": [],
                    "row_count": 0,
                }
            }

        rows_preview = query_result.rows[:_ROWS_PREVIEW_LIMIT]
        rows_preview_str = json.dumps(rows_preview, default=str, indent=2)

        result: ResultOutput = await self._chain.ainvoke(
            {
                "question": state["question"],
                "sql": query_result.sql,
                "row_count": query_result.row_count,
                "rows_preview": rows_preview_str,
            },
            config,
        )

        log.info("result formatted", extra={"row_count": query_result.row_count})

        return {
            "response": {
                "answer": result.answer,
                "sql": query_result.sql,
                "rows": query_result.rows,
                "row_count": query_result.row_count,
            }
        }
