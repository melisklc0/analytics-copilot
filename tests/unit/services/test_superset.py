from __future__ import annotations

import asyncio

import httpx
import pytest

from analytics_copilot.core.config import Settings
from analytics_copilot.core.exceptions import ConfigurationError, SupersetEmbedError
from analytics_copilot.services.superset import SupersetEmbedService

_INTERNAL = "http://superset:8088"


def _settings(**overrides: object) -> Settings:
    base: dict[str, object] = {
        "superset_dashboard_id": "5",
        "superset_internal_url": _INTERNAL,
        "superset_url": "http://localhost:8088",
        "superset_admin_user": "admin",
        "superset_embed_allowed_domains": "http://localhost:8502",
    }
    base.update(overrides)
    return Settings(**base)  # type: ignore[arg-type]


def _service(handler, **overrides: object) -> SupersetEmbedService:
    client = httpx.AsyncClient(
        transport=httpx.MockTransport(handler), base_url=_INTERNAL
    )
    return SupersetEmbedService(_settings(**overrides), client=client)


def _run(service: SupersetEmbedService):
    return asyncio.run(service.mint_guest_token())


def test_mint_uses_existing_embed_uuid() -> None:
    calls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        calls.append(f"{request.method} {path}")
        if path == "/api/v1/security/login":
            return httpx.Response(200, json={"access_token": "acc-token"})
        if path.endswith("/embedded") and request.method == "GET":
            return httpx.Response(200, json={"result": {"uuid": "UUID-EXISTING"}})
        if path == "/api/v1/security/guest_token/":
            assert request.headers["Authorization"] == "Bearer acc-token"
            return httpx.Response(200, json={"token": "GUEST-JWT"})
        return httpx.Response(500, json={"message": "unexpected"})

    result = _run(_service(handler))

    assert result.token == "GUEST-JWT"
    assert result.embed_uuid == "UUID-EXISTING"
    assert result.superset_domain == "http://localhost:8088"
    # Already embedded → no CSRF fetch, no enable POST.
    assert "GET /api/v1/security/csrf_token/" not in calls


def test_mint_auto_enables_embedding_when_missing() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if path == "/api/v1/security/login":
            return httpx.Response(200, json={"access_token": "acc-token"})
        if path.endswith("/embedded") and request.method == "GET":
            return httpx.Response(404, json={"message": "not embedded"})
        if path == "/api/v1/security/csrf_token/":
            return httpx.Response(200, json={"result": "CSRF-1"})
        if path.endswith("/embedded") and request.method == "POST":
            assert request.headers["X-CSRFToken"] == "CSRF-1"
            return httpx.Response(200, json={"result": {"uuid": "UUID-NEW"}})
        if path == "/api/v1/security/guest_token/":
            return httpx.Response(200, json={"token": "GUEST-JWT-2"})
        return httpx.Response(500, json={"message": "unexpected"})

    result = _run(_service(handler))

    assert result.embed_uuid == "UUID-NEW"
    assert result.token == "GUEST-JWT-2"


def test_missing_dashboard_id_raises_configuration_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={})

    with pytest.raises(ConfigurationError):
        _run(_service(handler, superset_dashboard_id=""))


def test_superset_error_is_wrapped() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"message": "bad creds"})

    with pytest.raises(SupersetEmbedError):
        _run(_service(handler))
