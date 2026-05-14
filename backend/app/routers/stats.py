"""Stats endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Chunk, Document, Occurrence, Page
from ..schemas import StatsOut

router = APIRouter(prefix="/api", tags=["stats"])


@router.get("/stats", response_model=StatsOut)
def get_stats(db: Session = Depends(get_db)) -> StatsOut:
    document_count = db.query(func.count(Document.id)).scalar() or 0
    page_count = db.query(func.count(Page.id)).scalar() or 0
    indexed_pages = (
        db.query(func.count(Page.id)).filter(Page.text_length > 0).scalar() or 0
    )
    occurrence_count = db.query(func.count(Occurrence.id)).scalar() or 0
    chunk_count = db.query(func.count(Chunk.id)).scalar() or 0
    embedded_chunks = (
        db.query(func.count(Chunk.id)).filter(Chunk.embedding.isnot(None)).scalar() or 0
    )
    return StatsOut(
        document_count=document_count,
        page_count=page_count,
        indexed_pages=indexed_pages,
        occurrence_count=occurrence_count,
        chunk_count=chunk_count,
        embedded_chunks=embedded_chunks,
    )
