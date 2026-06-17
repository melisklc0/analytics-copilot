from __future__ import annotations

import logging
import pathlib
from typing import Any

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableConfig

from analytics_copilot.core.exceptions import SQLGenerationError
from analytics_copilot.services.manifest_parser import ManifestParser
from analytics_copilot.services.prompt_loader import load_prompt
from analytics_copilot.workflow.models import SQLOutput
from analytics_copilot.workflow.state import WorkflowState

log = logging.getLogger(__name__)


class SQLGeneratorNode:
    def __init__(
        self,
        manifest: ManifestParser,
        llm: BaseChatModel,
        prompts_dir: pathlib.Path,
    ) -> None:
        self._manifest = manifest
        template = load_prompt(prompts_dir, "sql_generator")
        prompt = ChatPromptTemplate.from_messages(
            [
                ("system", template["system"]),
                ("human", template["user"]),
            ]
        )
        self._chain: Any = prompt | llm.with_structured_output(SQLOutput)

    async def __call__(
        self, state: WorkflowState, config: RunnableConfig
    ) -> dict[str, Any]:
        mart_context: str = state["mart_context"] or self._build_mart_context()
        validation_error = state["validation_error"]

        retry_note = (
            f"\n\n---\n\n## Previous SQL was rejected\n\n"
            f"Reason: {validation_error}\n\nPlease fix the SQL and try again."
            if validation_error
            else ""
        )

        updates: dict[str, Any] = {"mart_context": mart_context}
        if validation_error is not None:
            updates["retry_count"] = state["retry_count"] + 1

        try:
            result: SQLOutput = await self._chain.ainvoke(
                {
                    "question": state["question"],
                    "mart_context": mart_context,
                    "retry_note": retry_note,
                },
                config,
            )
            updates["sql"] = result.sql
            updates["error"] = None
        except SQLGenerationError as exc:
            log.warning("sql generation failed", extra={"error": str(exc)})
            updates["sql"] = None
            updates["error"] = str(exc)
        except Exception as exc:
            wrapped = SQLGenerationError(str(exc))
            log.exception("unexpected error during sql generation")
            updates["sql"] = None
            updates["error"] = str(wrapped)

        return updates

    def _build_mart_context(self) -> str:
        all_model_names = [m.name for m in self._manifest.get_all_models()]
        return self._manifest.get_context(all_model_names)
