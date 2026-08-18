"""Superset guest-token minting for embedded dashboards."""

from __future__ import annotations

import logging

import httpx

from analytics_copilot.core.config import Settings
from analytics_copilot.core.exceptions import ConfigurationError, SupersetEmbedError
from analytics_copilot.schemas.dashboard import GuestTokenResponse

log = logging.getLogger(__name__)


def _raise_for(response: httpx.Response, step: str) -> None:
    """Turn a non-2xx Superset response into a safe, logged SupersetEmbedError."""
    if response.is_success:
        return
    log.error(
        "Superset %s failed: status=%s body=%s",
        step,
        response.status_code,
        response.text[:300],
    )
    raise SupersetEmbedError(f"Superset {step} failed (status {response.status_code}).")


class SupersetEmbedService:
    def __init__(
        self, settings: Settings, *, client: httpx.AsyncClient | None = None
    ) -> None:
        self._s = settings
        # Injected in tests; in production a client is created per request so
        # its cookie jar (CSRF session) is scoped to a single mint.
        self._client = client

    async def mint_guest_token(self) -> GuestTokenResponse:
        dashboard = self._s.superset_dashboard_id.strip()
        if not dashboard:
            raise ConfigurationError("SUPERSET_DASHBOARD_ID is not set")

        if self._client is not None:
            return await self._flow(self._client, dashboard)
        try:
            async with httpx.AsyncClient(
                base_url=self._s.superset_internal_url, timeout=15.0
            ) as client:
                return await self._flow(client, dashboard)
        except httpx.HTTPError as exc:
            log.error("Superset request error: %s", exc, exc_info=True)
            raise SupersetEmbedError(
                "Could not reach Superset to mint a guest token."
            ) from exc

    async def _flow(
        self, client: httpx.AsyncClient, dashboard: str
    ) -> GuestTokenResponse:
        headers = {"Authorization": f"Bearer {await self._login(client)}"}
        embed_uuid = await self._ensure_embedded(client, headers, dashboard)
        token = await self._mint(client, headers, embed_uuid)
        return GuestTokenResponse(
            token=token,
            embed_uuid=embed_uuid,
            superset_domain=self._s.superset_url,
        )

    async def _login(self, client: httpx.AsyncClient) -> str:
        response = await client.post(
            "/api/v1/security/login",
            json={
                "username": self._s.superset_admin_user,
                "password": self._s.superset_admin_password.get_secret_value(),
                "provider": "db",
                "refresh": True,
            },
        )
        _raise_for(response, "login")
        return str(response.json()["access_token"])

    async def _csrf(self, client: httpx.AsyncClient, headers: dict[str, str]) -> str:
        response = await client.get("/api/v1/security/csrf_token/", headers=headers)
        _raise_for(response, "csrf")
        return str(response.json()["result"])

    async def _ensure_embedded(
        self, client: httpx.AsyncClient, headers: dict[str, str], dashboard: str
    ) -> str:
        # Already embed-enabled? A GET needs no CSRF.
        existing = await client.get(
            f"/api/v1/dashboard/{dashboard}/embedded", headers=headers
        )
        if existing.status_code == 200:
            result = existing.json().get("result") or {}
            if result.get("uuid"):
                return str(result["uuid"])

        # Not enabled yet — enable it. State-changing → needs CSRF + session.
        csrf = await self._csrf(client, headers)
        domains = [
            d.strip()
            for d in self._s.superset_embed_allowed_domains.split(",")
            if d.strip()
        ]
        created = await client.post(
            f"/api/v1/dashboard/{dashboard}/embedded",
            headers={
                **headers,
                "X-CSRFToken": csrf,
                "Referer": self._s.superset_internal_url,
            },
            json={"allowed_domains": domains},
        )
        _raise_for(created, "enable-embedded")
        return str(created.json()["result"]["uuid"])

    async def _mint(
        self, client: httpx.AsyncClient, headers: dict[str, str], embed_uuid: str
    ) -> str:
        response = await client.post(
            "/api/v1/security/guest_token/",
            headers=headers,
            json={
                "user": {
                    "username": "embed-guest",
                    "first_name": "Embed",
                    "last_name": "Guest",
                },
                "resources": [{"type": "dashboard", "id": embed_uuid}],
                "rls": [],
            },
        )
        _raise_for(response, "guest-token")
        return str(response.json()["token"])
