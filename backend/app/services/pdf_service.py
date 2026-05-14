"""PDF processing pipeline: extract text, OCR fallback, render page images,
extract entities, build FTS index and chunk embeddings."""
from __future__ import annotations

import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Iterable, List, Optional

import fitz  # PyMuPDF
import numpy as np
from sqlalchemy.orm import Session

from ..config import settings
from ..database import raw_sqlite, session_scope
from ..models import Chunk, Document, Occurrence, Page
from . import embedding_service, extraction_service, llm_service, ocr_service

logger = logging.getLogger(__name__)


def _doc_image_dir(document_id: int) -> Path:
    p = settings.page_images_dir / f"doc_{document_id}"
    p.mkdir(parents=True, exist_ok=True)
    return p


def _read_pdf_metadata(pdf_path: Path) -> dict:
    try:
        with fitz.open(pdf_path) as doc:
            md = doc.metadata or {}
            return {
                "title": (md.get("title") or "").strip() or None,
                "author": (md.get("author") or "").strip() or None,
                "page_count": doc.page_count,
            }
    except Exception as e:
        logger.warning("Failed to read PDF metadata for %s: %s", pdf_path, e)
        return {"title": None, "author": None, "page_count": 0}


def init_document(db: Session, file_name: str, stored_path: Path) -> Document:
    md = _read_pdf_metadata(stored_path)
    doc = Document(
        file_name=file_name,
        stored_path=str(stored_path),
        title=md.get("title") or file_name,
        author=md.get("author"),
        page_count=md.get("page_count") or 0,
        status="pending",
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return doc


def _render_page_image(page: "fitz.Page", out_path: Path) -> Optional[str]:
    try:
        zoom = settings.page_image_dpi / 72.0
        mat = fitz.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=mat, alpha=False)
        pix.save(str(out_path))
        return str(out_path)
    except Exception as e:
        logger.warning("Render page image failed: %s", e)
        return None


def _extract_text_with_fallback(page: "fitz.Page", image_path: Optional[Path]) -> tuple[str, bool]:
    """Returns (text, ocr_used)."""
    text = ""
    try:
        text = page.get_text("text") or ""
    except Exception:
        text = ""
    text = text.strip()

    if len(text) >= 30:
        return text, False

    # OCR fallback
    if not ocr_service.is_available():
        return text, False
    try:
        if image_path and image_path.exists():
            with open(image_path, "rb") as f:
                png_bytes = f.read()
        else:
            zoom = settings.page_image_dpi / 72.0
            pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom), alpha=False)
            png_bytes = pix.tobytes("png")
        ocr_text = ocr_service.ocr_image_bytes(png_bytes).strip()
        if ocr_text:
            return ocr_text, True
    except Exception as e:
        logger.warning("OCR fallback failed: %s", e)
    return text, False


# ---------------------------------------------------------------------------
# Chunking
# ---------------------------------------------------------------------------
def _split_into_chunks(text: str, target_chars: int = 800, overlap: int = 100) -> List[str]:
    """Simple character-based chunking that respects paragraph and sentence breaks."""
    text = text.strip()
    if not text:
        return []
    # Try paragraph splits first
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    chunks: List[str] = []
    buf = ""
    for para in paragraphs:
        if len(buf) + len(para) + 1 <= target_chars:
            buf = (buf + "\n" + para).strip()
        else:
            if buf:
                chunks.append(buf)
            if len(para) <= target_chars:
                buf = para
            else:
                # Long paragraph, hard split.
                start = 0
                while start < len(para):
                    end = min(len(para), start + target_chars)
                    chunks.append(para[start:end])
                    start = end - overlap if end - overlap > start else end
                buf = ""
    if buf:
        chunks.append(buf)
    return [c for c in chunks if c.strip()]


# ---------------------------------------------------------------------------
# FTS5
# ---------------------------------------------------------------------------
def _fts_delete_document(document_id: int) -> None:
    with raw_sqlite() as conn:
        conn.execute("DELETE FROM pages_fts WHERE document_id = ?", (document_id,))
        conn.commit()


def _fts_insert_pages(rows: Iterable[tuple[int, int, int, str]]) -> None:
    with raw_sqlite() as conn:
        conn.executemany(
            "INSERT INTO pages_fts(page_id, document_id, page_number, text) "
            "VALUES (?, ?, ?, ?)",
            list(rows),
        )
        conn.commit()


# ---------------------------------------------------------------------------
# Main processing pipeline
# ---------------------------------------------------------------------------
def process_document(document_id: int, use_llm: bool = True) -> None:
    """Process a single document. Designed to be called from a thread."""
    with session_scope() as db:
        doc = db.get(Document, document_id)
        if not doc:
            logger.warning("Document %s vanished before processing", document_id)
            return
        doc.status = "processing"
        doc.error = None
        db.commit()

    try:
        _process_document_inner(document_id, use_llm=use_llm)
        with session_scope() as db:
            doc = db.get(Document, document_id)
            if doc:
                doc.status = "completed"
                doc.processed_at = datetime.utcnow()
    except Exception as e:
        logger.exception("Processing failed for document %s", document_id)
        with session_scope() as db:
            doc = db.get(Document, document_id)
            if doc:
                doc.status = "failed"
                doc.error = str(e)[:1000]


def _process_document_inner(document_id: int, use_llm: bool) -> None:
    with session_scope() as db:
        doc = db.get(Document, document_id)
        if not doc:
            return
        pdf_path = Path(doc.stored_path)
        # Clear existing data so we can re-process.
        for p in list(doc.pages):
            db.delete(p)
        for o in list(doc.occurrences):
            db.delete(o)
        for c in list(doc.chunks):
            db.delete(c)
        db.commit()

    _fts_delete_document(document_id)

    img_dir = _doc_image_dir(document_id)

    # First pass: extract text and render images, persist pages.
    page_records: List[dict] = []
    try:
        with fitz.open(pdf_path) as pdf:
            page_count = pdf.page_count
            with session_scope() as db:
                doc = db.get(Document, document_id)
                if doc:
                    doc.page_count = page_count
                    db.commit()

            for idx in range(page_count):
                page = pdf.load_page(idx)
                page_no = idx + 1
                img_path = img_dir / f"page_{page_no:04d}.png"
                _render_page_image(page, img_path)
                text, ocr_used = _extract_text_with_fallback(page, img_path)
                page_records.append(
                    {
                        "page_number": page_no,
                        "page_label": page.get_label() or str(page_no),
                        "text": text or "",
                        "ocr_used": 1 if ocr_used else 0,
                        "text_length": len(text or ""),
                        "image_path": str(img_path),
                    }
                )
    except Exception as e:
        raise RuntimeError(f"Failed to read PDF: {e}") from e

    # Persist page rows
    page_ids: List[int] = []
    with session_scope() as db:
        for rec in page_records:
            p = Page(
                document_id=document_id,
                page_number=rec["page_number"],
                page_label=rec["page_label"],
                text=rec["text"],
                ocr_used=rec["ocr_used"],
                text_length=rec["text_length"],
                image_path=rec["image_path"],
            )
            db.add(p)
            db.flush()
            page_ids.append(p.id)
            rec["page_id"] = p.id
        db.commit()

    # FTS insert
    fts_rows = [
        (rec["page_id"], document_id, rec["page_number"], rec["text"])
        for rec in page_records
        if rec["text"]
    ]
    if fts_rows:
        _fts_insert_pages(fts_rows)

    # Rule + LLM extraction; collect occurrences and chunks per page.
    chunk_payload: List[dict] = []
    occurrences_payload: List[dict] = []

    for rec in page_records:
        text = rec["text"]
        if not text:
            continue

        # Rule extraction
        for ext in extraction_service.extract_all(text):
            occurrences_payload.append(
                {
                    "document_id": document_id,
                    "page_id": rec["page_id"],
                    "term": ext.term,
                    "term_type": ext.term_type,
                    "start_char": ext.start,
                    "end_char": ext.end,
                    "context": ext.context,
                    "confidence": ext.confidence,
                    "extractor": "rule",
                }
            )

        # LLM extraction (best-effort; failures are non-fatal)
        if use_llm and llm_service.is_enabled():
            try:
                llm_out = llm_service.extract_from_page(text)
            except Exception:
                llm_out = None
            if llm_out:
                # Map LLM fields to occurrence types.
                mapping = [
                    ("scientific_names", "scientific_name", 0.9),
                    ("chinese_names", "chinese_name", 0.8),
                    ("locations", "location", 0.7),
                    ("keywords", "keyword", 0.6),
                ]
                for key, term_type, conf in mapping:
                    for raw_term in llm_out.get(key, []):
                        term = raw_term.strip()
                        if not term:
                            continue
                        # Verify presence in page text. If not present, skip
                        # (LLM hallucination guard).
                        if term not in text and term.lower() not in text.lower():
                            continue
                        idx = text.lower().find(term.lower())
                        ctx = ""
                        if idx >= 0:
                            ctx = extraction_service._context_window(
                                text, idx, idx + len(term)
                            )
                        occurrences_payload.append(
                            {
                                "document_id": document_id,
                                "page_id": rec["page_id"],
                                "term": term,
                                "term_type": term_type,
                                "start_char": idx,
                                "end_char": idx + len(term) if idx >= 0 else -1,
                                "context": ctx,
                                "confidence": conf,
                                "extractor": "llm",
                            }
                        )

        # Build chunks per page
        chunks = _split_into_chunks(text, target_chars=800, overlap=100)
        for ci, chunk_text in enumerate(chunks):
            chunk_payload.append(
                {
                    "document_id": document_id,
                    "page_id": rec["page_id"],
                    "chunk_index": ci,
                    "text": chunk_text,
                    "token_count": max(1, len(chunk_text) // 3),
                }
            )

    # Persist occurrences and chunks
    with session_scope() as db:
        if occurrences_payload:
            db.bulk_insert_mappings(Occurrence, occurrences_payload)
        if chunk_payload:
            db.bulk_insert_mappings(Chunk, chunk_payload)
        db.commit()

    # Embeddings (optional, batched)
    if chunk_payload:
        _embed_chunks_for_document(document_id)


def _embed_chunks_for_document(document_id: int) -> None:
    """Compute embeddings for the chunks of a document, in batches."""
    with session_scope() as db:
        rows = (
            db.query(Chunk)
            .filter(Chunk.document_id == document_id)
            .order_by(Chunk.id.asc())
            .all()
        )
        if not rows:
            return
        # Probe provider availability before iterating
        sample = embedding_service.embed_texts([rows[0].text[:200]])
        if sample is None:
            logger.info("No embedding provider available; skipping embeddings.")
            return

        batch_size = 16
        for i in range(0, len(rows), batch_size):
            batch = rows[i : i + batch_size]
            texts = [r.text for r in batch]
            arr = embedding_service.embed_texts(texts)
            if arr is None:
                logger.warning("Embedding provider became unavailable mid-job.")
                return
            for r, vec in zip(batch, arr):
                r.embedding = np.asarray(vec, dtype=np.float32).tobytes()
            db.commit()


# ---------------------------------------------------------------------------
# Page snapshot helpers
# ---------------------------------------------------------------------------
def page_image_path(document_id: int, page_number: int) -> Optional[Path]:
    p = settings.page_images_dir / f"doc_{document_id}" / f"page_{page_number:04d}.png"
    if p.exists():
        return p
    return None


def delete_document_files(document_id: int, stored_path: Optional[str]) -> None:
    """Delete uploaded PDF and rendered page images for a document."""
    if stored_path:
        try:
            Path(stored_path).unlink(missing_ok=True)
        except Exception:
            pass
    img_dir = settings.page_images_dir / f"doc_{document_id}"
    if img_dir.exists():
        try:
            for f in img_dir.iterdir():
                f.unlink(missing_ok=True)
            img_dir.rmdir()
        except Exception:
            pass
    _fts_delete_document(document_id)
