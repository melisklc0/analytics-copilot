from __future__ import annotations

from pydantic import BaseModel


class GuestTokenResponse(BaseModel):
    """A short-lived Superset guest token plus what the SDK needs to mount.

    ``token``           — the guest JWT, valid for a few minutes.
    ``embed_uuid``      — the dashboard's embedded UUID (the SDK's ``id``).
    ``superset_domain`` — the browser-reachable Superset origin.
    """

    token: str
    embed_uuid: str
    superset_domain: str
