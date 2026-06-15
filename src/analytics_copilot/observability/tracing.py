import logging
from functools import lru_cache

from langfuse import Langfuse

from analytics_copilot.core.config import get_settings

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def get_langfuse() -> Langfuse | None:
    """Return a configured Langfuse client, or None if keys are not set."""
    settings = get_settings()
    if not settings.langfuse_public_key or not settings.langfuse_secret_key:
        logger.info("Langfuse tracing disabled — keys not configured")
        return None
    client = Langfuse(
        public_key=settings.langfuse_public_key.get_secret_value(),
        secret_key=settings.langfuse_secret_key.get_secret_value(),
        host=settings.langfuse_host,
    )
    logger.info(
        "Langfuse tracing enabled",
        extra={"langfuse_host": settings.langfuse_host},
    )
    return client


def flush_langfuse() -> None:
    """Flush any queued Langfuse events — call on application shutdown."""
    client = get_langfuse()
    if client is not None:
        client.flush()
