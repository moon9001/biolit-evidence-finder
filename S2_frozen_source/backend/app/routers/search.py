"""Search and export endpoints."""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import PlainTextResponse, Response
from sqlalchemy.orm import Session

from ..database import get_db
from ..schemas import SearchResponse
from ..services import export_service, search_service

router = APIRouter(prefix="/api", tags=["search"])


@router.get("/search", response_model=SearchResponse)
def search(
    q: str = Query(..., min_length=1),
    mode: str = Query("hybrid"),
    limit: int = Query(50, ge=1, le=500),
    db: Session = Depends(get_db),
):
    items, note = search_service.search(db, q, mode, limit=limit)
    search_service.log_search(db, q, mode, len(items))
    return SearchResponse(
        query=q,
        mode=mode,
        result_count=len(items),
        results=items,
        notes=note,
    )


@router.get("/export/search-results")
def export_search(
    q: str = Query(..., min_length=1),
    mode: str = Query("hybrid"),
    format: str = Query("csv"),
    limit: int = Query(500, ge=1, le=5000),
    db: Session = Depends(get_db),
):
    items, _note = search_service.search(db, q, mode, limit=limit)
    fmt = format.lower().strip()
    if fmt == "json":
        body = export_service.to_json(items, q, mode)
        return Response(
            content=body,
            media_type="application/json",
            headers={
                "Content-Disposition": f'attachment; filename="search_{mode}.json"'
            },
        )
    if fmt != "csv":
        raise HTTPException(status_code=400, detail="format must be csv or json")
    body = export_service.to_csv(items)
    return PlainTextResponse(
        body,
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="search_{mode}.csv"'
        },
    )
