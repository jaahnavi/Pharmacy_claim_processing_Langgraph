"""Application settings loaded from .env."""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT_DIR = Path(__file__).resolve().parent.parent
load_dotenv(ROOT_DIR / ".env")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(ROOT_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_host: str = "0.0.0.0"
    app_port: int = 8000
    app_base_url: str = "http://localhost:8000"
    disclaimer: str = (
        "Educational demo only. Not for real insurance billing, medical advice, or PHI. "
        "Use synthetic member/claim data only."
    )
    checkpoint_db_path: str = "./data/checkpoints.sqlite"
    log_level: str = "INFO"

    llm_provider: str = "openai"  # openai | azure

    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    openai_base_url: str = "https://api.openai.com/v1"

    azure_openai_api_key: str = ""
    azure_openai_endpoint: str = ""
    azure_openai_api_version: str = "2024-08-01-preview"
    azure_openai_deployment: str = "gpt-4o-mini"

    llm1_temperature: float = 0.1
    llm2_temperature: float = 0.2
    llm_timeout_seconds: int = 30
    llm_force_fallback: bool = False

    langchain_tracing_v2: bool = False
    langchain_api_key: str = ""
    langchain_project: str = "pharmacy-claim-orchestration"
    langchain_endpoint: str = "https://api.smith.langchain.com"

    http_timeout_seconds: float = 15.0
    http_max_retries: int = 3

    eval_use_llm_judge: bool = False
    eval_judge_model: str = "gpt-4o-mini"

    # Public APIs
    rxnorm_base_url: str = "https://rxnav.nlm.nih.gov/REST"
    openfda_base_url: str = "https://api.fda.gov/drug/ndc.json"
    npi_registry_url: str = "https://npiregistry.cms.hhs.gov/api/"


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    # Propagate LangSmith env for LangChain auto-instrumentation
    if settings.langchain_tracing_v2 and settings.langchain_api_key:
        os.environ["LANGCHAIN_TRACING_V2"] = "true"
        os.environ["LANGCHAIN_API_KEY"] = settings.langchain_api_key
        os.environ["LANGCHAIN_PROJECT"] = settings.langchain_project
        os.environ["LANGCHAIN_ENDPOINT"] = settings.langchain_endpoint
    return settings
