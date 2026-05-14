"""Document upload, processing, listing, files."""
from __future__ import annotations

import logging
import unicodedata
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from ..config import settings
from ..database import get_db
from ..models import Document, Page
from ..schemas import DocumentListResponse, DocumentOut, PageOut
from ..services import pdf_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/documents", tags=["documents"])

# Single-worker executor: PDF processing is heavy (PyMuPDF + LLM extraction +
# embedding API) and concurrent processing both starves SQLite (write locks)
# and trips per-tenant rate limits on LLM/embedding endpoints. Serialising
# the workload through one worker is far more reliable; the queue itself is
# unbounded so users can still upload as many PDFs as they want at once.
_processing_executor = ThreadPoolExecutor(
    max_workers=1, thread_name_prefix="biolit-pdf"
)


def _safe_filename(name: str) -> str:
    name = unicodedata.normalize("NFKC", name)
    name = name.replace("\\", "/").split("/")[-1]
    name = "".join(c for c in name if c.isprintable())
    if not name:
        name = "upload.pdf"
    return name[:200]


@router.post("/upload", response_model=List[DocumentOut])
async def upload_documents(
    background_tasks: BackgroundTasks,
    files: List[UploadFile] = File(...),
    auto_process: bool = True,
    db: Session = Depends(get_db),
):
    if not files:
        raise HTTPException(status_code=400, detail="No files uploaded.")
    out: List[DocumentOut] = []
    for f in files:
        if not f.filename:
            continue
        safe = _safe_filename(f.filename)
        if not safe.lower().endswith(".pdf"):
            raise HTTPException(
                status_code=400, detail=f"Only PDF files are supported: {safe}"
            )
        ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S_%f")
        stored = settings.uploads_dir / f"{ts}__{safe}"
        try:
            with open(stored, "wb") as w:
                while True:
                    chunk = await f.read(1024 * 1024)
                    if not chunk:
                        break
                    w.write(chunk)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to save file: {e}")

        try:
            doc = pdf_service.init_document(db, file_name=safe, stored_path=stored)
        except Exception as e:
            try:
                stored.unlink(missing_ok=True)
            except Exception:
                pass
            raise HTTPException(status_code=400, detail=f"Invalid PDF: {e}")

        if auto_process:
            doc_id = doc.id
            background_tasks.add_task(_run_processing, doc_id)

        out.append(DocumentOut.model_validate(doc))
    return out


def _run_processing(doc_id: int) -> None:
    """Submit processing work to the single-worker executor so PDFs are
    handled one at a time. Returns immediately."""
    _processing_executor.submit(pdf_service.process_document, doc_id)


@router.get("", response_model=DocumentListResponse)
def list_documents(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    status: Optional[str] = Query(
        None, description="Filter by status: pending|queued|processing|completed|failed"
    ),
    q: Optional[str] = Query(
        None, description="Filter by file name or title (case-insensitive substring)"
    ),
    db: Session = Depends(get_db),
):
    base = db.query(Document)
    if status:
        # Allow comma-separated multi-status filter, e.g. status=processing,queued
        statuses = [s.strip() for s in status.split(",") if s.strip()]
        if len(statuses) == 1:
            base = base.filter(Document.status == statuses[0])
        elif len(statuses) > 1:
            base = base.filter(Document.status.in_(statuses))
    if q:
        like = f"%{q.strip()}%"
        base = base.filter(or_(Document.file_name.ilike(like),
                               Document.title.ilike(like)))

    total = base.with_entities(func.count(Document.id)).scalar() or 0

    items = (
        base.order_by(Document.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    # Status histogram is always computed against the unfiltered table so the
    # tab counts in the UI stay stable regardless of which filter is active.
    raw_counts = (
        db.query(Document.status, func.count(Document.id))
        .group_by(Document.status)
        .all()
    )
    status_counts = {s: c for s, c in raw_counts}
    status_counts["all"] = sum(status_counts.values())

    return DocumentListResponse(
        items=[DocumentOut.model_validate(d) for d in items],
        total=total,
        page=page,
        page_size=page_size,
        status_counts=status_counts,
    )


@router.get("/{doc_id}", response_model=DocumentOut)
def get_document(doc_id: int, db: Session = Depends(get_db)):
    d = db.get(Document, doc_id)
    if not d:
        raise HTTPException(status_code=404, detail="Document not found")
    return DocumentOut.model_validate(d)


@router.delete("/{doc_id}")
def delete_document(doc_id: int, db: Session = Depends(get_db)):
    d = db.get(Document, doc_id)
    if not d:
        raise HTTPException(status_code=404, detail="Document not found")
    stored_path = d.stored_path
    db.delete(d)
    db.commit()
    pdf_service.delete_document_files(doc_id, stored_path)
    return {"deleted": doc_id}


@router.post("/{doc_id}/process")
def process_document(
    doc_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    d = db.get(Document, doc_id)
    if not d:
        raise HTTPException(status_code=404, detail="Document not found")
    if d.status == "processing":
        return {"status": "already_processing", "document_id": doc_id}
    background_tasks.add_task(_run_processing, doc_id)
    d.status = "queued"
    db.commit()
    return {"status": "queued", "document_id": doc_id}


@router.get("/{doc_id}/pages", response_model=List[PageOut])
def list_pages(doc_id: int, db: Session = Depends(get_db)):
    pages = (
        db.query(Page)
        .filter(Page.document_id == doc_id)
        .order_by(Page.page_number.asc())
        .all()
    )
    return [PageOut.model_validate(p) for p in pages]


@router.get("/{doc_id}/pages/{page_number}", response_model=PageOut)
def get_page(doc_id: int, page_number: int, db: Session = Depends(get_db)):
    p = (
        db.query(Page)
        .filter(Page.document_id == doc_id, Page.page_number == page_number)
        .first()
    )
    if not p:
        raise HTTPException(status_code=404, detail="Page not found")
    return PageOut.model_validate(p)


@router.get("/{doc_id}/file")
def get_file(doc_id: int, db: Session = Depends(get_db)):
    d = db.get(Document, doc_id)
    if not d:
        raise HTTPException(status_code=404, detail="Document not found")
    p = Path(d.stored_path)
    if not p.exists():
        raise HTTPException(status_code=404, detail="Stored file missing")
    return FileResponse(p, media_type="application/pdf", filename=d.file_name)


@router.get("/{doc_id}/page-image/{page_number}")
def get_page_image(doc_id: int, page_number: int):
    p = pdf_service.page_image_path(doc_id, page_number)
    if not p:
        return JSONResponse(
            status_code=404, content={"detail": "Page image not available"}
        )
    return FileResponse(p, media_type="image/png")
