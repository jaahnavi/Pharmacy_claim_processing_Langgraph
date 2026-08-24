"""Shared LLM client factory (OpenAI / Azure OpenAI from .env)."""

from __future__ import annotations

from functools import lru_cache
from typing import Any

from langchain_openai import AzureChatOpenAI, ChatOpenAI

from app.config import get_settings


@lru_cache
def get_chat_model(temperature: float = 0.1) -> Any:
    settings = get_settings()
    provider = (settings.llm_provider or "openai").lower()
    if provider == "azure":
        return AzureChatOpenAI(
            azure_endpoint=settings.azure_openai_endpoint,
            api_key=settings.azure_openai_api_key,
            api_version=settings.azure_openai_api_version,
            azure_deployment=settings.azure_openai_deployment,
            temperature=temperature,
            timeout=settings.llm_timeout_seconds,
        )
    return ChatOpenAI(
        api_key=settings.openai_api_key or "missing",
        model=settings.openai_model,
        base_url=settings.openai_base_url,
        temperature=temperature,
        timeout=settings.llm_timeout_seconds,
    )


def llm_configured() -> bool:
    settings = get_settings()
    provider = (settings.llm_provider or "openai").lower()
    if provider == "azure":
        return bool(settings.azure_openai_api_key and settings.azure_openai_endpoint)
    return bool(settings.openai_api_key) and not settings.openai_api_key.startswith("sk-your")
