from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends

from langfuse.langchain import CallbackHandler

from analytics_copilot.api.dependencies import get_graph, get_langfuse_handler
from analytics_copilot.schemas.query import QueryRequest, QueryResponse

router = APIRouter(prefix="/query", tags=["query"])
log = logging.getLogger(__name__)


def _initial_state(question: str) -> dict[str, Any]:
    return {
        "question": question,
        "mart_context": None,
        "sql": None,
        "validation_status": None,
        "validation_error": None,
        "query_result": None,
        "retry_count": 0,
        "error": None,
        "response": None,
    }


@router.post("", response_model=QueryResponse)
async def query(
    body: QueryRequest,
    graph: Any = Depends(get_graph),
    langfuse_handler: CallbackHandler | None = Depends(get_langfuse_handler),
) -> QueryResponse:
    log.info("query received", extra={"question": body.question})

    config: dict[str, Any] = {"callbacks": [langfuse_handler]} if langfuse_handler else {}
    result: dict[str, Any] = await graph.ainvoke(_initial_state(body.question), config)

    query_result = result.get("query_result")
    response: dict[str, Any] = result.get("response") or {}

    log.info(
        "workflow completed",
        extra={
            "sql": result.get("sql"),
            "retry_count": result.get("retry_count", 0),
            "row_count": query_result.row_count if query_result else 0,
            "error": result.get("error"),
        },
    )

    return QueryResponse(
        answer=str(response.get("answer", "")),
        sql=result.get("sql"),
        rows=list(query_result.rows) if query_result else [],
        row_count=int(query_result.row_count) if query_result else 0,
        retry_count=int(result.get("retry_count", 0)),
        error=result.get("error"),
    )
