from __future__ import annotations

from typing import Any

from fastapi import Request
from langfuse.langchain import CallbackHandler

from analytics_copilot.core.context import request_id_var
from analytics_copilot.observability.tracing import get_langfuse


def get_graph(request: Request) -> Any:
    """FastAPI dependency — returns the compiled LangGraph graph from app state."""
    return request.app.state.graph


def get_langfuse_handler() -> CallbackHandler | None:
    """Per-request Langfuse callback handler, keyed by request ID."""
    client = get_langfuse()
    if client is None:
        return None
    request_id = request_id_var.get() or None
    return client.get_langchain_handler(
        trace_id=request_id,
        session_id=request_id,
    )
