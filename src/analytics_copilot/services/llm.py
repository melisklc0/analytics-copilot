from __future__ import annotations

import logging
from functools import lru_cache

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_openai import ChatOpenAI

from analytics_copilot.core.config import get_settings
from analytics_copilot.core.exceptions import ConfigurationError

log = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def get_llm() -> BaseChatModel:
    settings = get_settings()
    if settings.llm_provider == "openrouter":
        if not settings.openrouter_api_key:
            raise ConfigurationError(
                "OPENROUTER_API_KEY is required when LLM_PROVIDER=openrouter"
            )
        log.info(
            "LLM initialized",
            extra={"provider": "openrouter", "model": settings.openrouter_model},
        )
        return ChatOpenAI(
            model=settings.openrouter_model,
            temperature=0,
            base_url=settings.openrouter_base_url,
            api_key=settings.openrouter_api_key,
        )
    if settings.llm_provider == "openai":
        if not settings.openai_api_key:
            raise ConfigurationError(
                "OPENAI_API_KEY is required when LLM_PROVIDER=openai"
            )
        log.info(
            "LLM initialized",
            extra={"provider": "openai", "model": settings.openai_model},
        )
        return ChatOpenAI(
            model=settings.openai_model,
            temperature=0,
            api_key=settings.openai_api_key,
        )
    raise ConfigurationError(f"Unsupported LLM provider: {settings.llm_provider}")
