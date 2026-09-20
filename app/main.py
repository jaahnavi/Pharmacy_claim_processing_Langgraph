"""FastAPI entrypoint for pharmacy claim orchestration."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import __version__
from app.api import approvals, claims, local
from app.config import get_settings
from app.llm.client import llm_configured


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Ensure checkpoint dir exists / graph warms
    from app.graph.graph import get_compiled_graph

    get_compiled_graph()
    yield


settings = get_settings()

app = FastAPI(
    title="LangGraph Pharmacy Claim Orchestration",
    description=settings.disclaimer,
    version=__version__,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(claims.router)
app.include_router(approvals.router)
app.include_router(local.router)


@app.get("/health")
def health() -> dict:
    return {
        "status": "ok",
        "version": __version__,
        "llm_configured": llm_configured(),
        "llm_provider": settings.llm_provider,
        "checkpoint_backend": settings.checkpoint_backend,
        "langsmith_tracing": settings.langchain_tracing_v2,
        "disclaimer": settings.disclaimer,
        "dependencies": {
            "rxnorm": settings.rxnorm_base_url,
            "openfda": settings.openfda_base_url,
            "npi_registry": settings.npi_registry_url,
        },
    }


@app.get("/")
def root() -> dict:
    return {
        "service": "LangGraph Pharmacy Claim Orchestration",
        "disclaimer": settings.disclaimer,
        "docs": "/docs",
        "health": "/health",
    }
