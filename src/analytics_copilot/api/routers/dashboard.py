from __future__ import annotations

import logging

from fastapi import APIRouter, Depends

from analytics_copilot.api.dependencies import get_embed_service
from analytics_copilot.schemas.dashboard import GuestTokenResponse
from analytics_copilot.services.superset import SupersetEmbedService

router = APIRouter(prefix="/dashboard", tags=["dashboard"])
log = logging.getLogger(__name__)


@router.post("/guest-token", response_model=GuestTokenResponse)
async def guest_token(
    service: SupersetEmbedService = Depends(get_embed_service),
) -> GuestTokenResponse:
    """Mint a short-lived Superset guest token for the embedded dashboard.

    No user auth: the console is unauthenticated, so this endpoint is open.
    Exposure is bounded (read-only guest scope, one dashboard, short-lived
    token) — do not expose publicly without adding auth.
    """
    log.info("guest token requested")
    return await service.mint_guest_token()
