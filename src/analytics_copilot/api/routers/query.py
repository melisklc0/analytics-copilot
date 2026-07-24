from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from typing import Any

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from langfuse.langchain import CallbackHandler

from analytics_copilot.api.dependencies import get_graph, get_langfuse_handler
from analytics_copilot.schemas.query import QueryRequest, QueryResponse, TraceEvent
from analytics_copilot.workflow.service import (
    final_payload,
    initial_state,
    stream_query_events,
)

router = APIRouter(prefix="/query", tags=["query"])
log = logging.getLogger(__name__)


def _run_config(handler: CallbackHandler | None) -> dict[str, Any]:
    return {"callbacks": [handler]} if handler else {}


@router.post("", response_model=QueryResponse)
async def query(
    body: QueryRequest,
    graph: Any = Depends(get_graph),
    langfuse_handler: CallbackHandler | None = Depends(get_langfuse_handler),
) -> QueryResponse:
    log.info("query received", extra={"question": body.question})

    result: dict[str, Any] = await graph.ainvoke(
        initial_state(body.question), _run_config(langfuse_handler)
    )
    payload = final_payload(result)

    log.info(
        "workflow completed",
        extra={
            "sql": payload["sql"],
            "retry_count": payload["retry_count"],
            "row_count": payload["row_count"],
            "error": payload["error"],
        },
    )
    return QueryResponse(**payload)


@router.post("/stream")
async def query_stream(
    body: QueryRequest,
    graph: Any = Depends(get_graph),
    langfuse_handler: CallbackHandler | None = Depends(get_langfuse_handler),
) -> StreamingResponse:
    """Run the workflow with real-time SSE, one event per pipeline node.

    Event types (see schemas.query.TraceEvent):
      node   — a node finished (sql_generator/sql_validator/sql_executor/...)
      final  — the workflow ended; carries the QueryResponse fields
      error  — the stream failed; carries a safe message (details are logged)
    """
    log.info("query stream received", extra={"question": body.question})
    config = _run_config(langfuse_handler)

    async def event_generator() -> AsyncIterator[str]:
        try:
            async for event in stream_query_events(graph, body.question, config):
                yield f"data: {event.model_dump_json()}\n\n"
        except Exception:
            log.exception("query stream failed")
            err = TraceEvent(type="error", data={"message": "Workflow failed."})
            yield f"data: {err.model_dump_json()}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")
