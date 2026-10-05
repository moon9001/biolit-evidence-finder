"""BioLitEvidence Finder backend entry point."""
from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .database import init_db
from .routers import documents, search, settings as settings_router, stats

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

app = FastAPI(
    title="BioLitEvidence Finder",
    version="0.1.0",
    description=(
        "Page-level evidence discovery for biodiversity literature. "
        "Upload PDFs, extract text + names, and search by keyword, "
        "scientific name, full-text or semantic similarity."
    ),
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def _startup() -> None:
    init_db()


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok", "service": "BioLitEvidence Finder"}


app.include_router(documents.router)
app.include_router(search.router)
app.include_router(settings_router.router)
app.include_router(stats.router)
