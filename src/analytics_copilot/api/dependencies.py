from __future__ import annotations

from typing import Any

from fastapi import Request


def get_graph(request: Request) -> Any:
    """FastAPI dependency — returns the compiled LangGraph graph from app state."""
    return request.app.state.graph
