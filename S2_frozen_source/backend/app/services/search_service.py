"""Search service: exact / scientific / fulltext / semantic / hybrid."""
from __future__ import annotations

import logging
import re
from typing import Dict, List, Optional, Tuple
from urllib.parse import quote

import numpy as np
from sqlalchemy import or_
from sqlalchemy.orm import Session

from ..database import IS_SQLITE, raw_sqlite
from ..models import Chunk, Document, Occurrence, Page, SearchLog
from ..schemas import SearchResultItem
from . import embedding_service

logger = logging.getLogger(__name__)


def _viewer_url(document_id: int, page_number: int, q: str, mode: str) -> str:
    return f"/viewer/{document_id}?page={page_number}&q={quote(q)}&mode={mode}"


def _context_around(text: str, term: str, radius: int = 100) -> Tuple[str, int]:
    if not text or not term:
        return text[:200], -1
    idx = text.lower().find(term.lower())
    if idx < 0:
        return text[:200].replace("\n", " "), -1
    s = max(0, idx - radius)
    e = min(len(text), idx + len(term) + radius)
    return re.sub(r"\s+", " ", text[s:e]).strip(), idx


def log_search(db: Session, query: str, mode: str, count: int) -> None:
    try:
        db.add(SearchLog(query=query[:1024], mode=mode, result_count=count))
        db.commit()
    except Exception:
        db.rollback()


# --------------------------------------------------------------------------- #
# Exact (page text contains, case-insensitive)
# --------------------------------------------------------------------------- #
def search_exact(
    db: Session, query: str, limit: int = 50
) -> List[SearchResultItem]:
    q = query.strip()
    if not q:
        return []
    pattern = f"%{q}%"
    rows = (
        db.query(Page, Document)
        .join(Document, Document.id == Page.document_id)
        .filter(Page.text.ilike(pattern))
        .order_by(Page.document_id.asc(), Page.page_number.asc())
        .limit(limit)
        .all()
    )
    out: List[SearchResultItem] = []
    for page, doc in rows:
        ctx, _ = _context_around(page.text, q)
        out.append(
            SearchResultItem(
                document_id=doc.id,
                document_title=doc.title or doc.file_name,
                file_name=doc.file_name,
                page_number=page.page_number,
                matched_term=q,
                context=ctx,
                score=1.0,
                match_type="exact",
                viewer_url=_viewer_url(doc.id, page.page_number, q, "exact"),
            )
        )
    return out


# --------------------------------------------------------------------------- #
# Scientific name search via occurrences
# --------------------------------------------------------------------------- #
def search_scientific(
    db: Session, query: str, limit: int = 50
) -> List[SearchResultItem]:
    q = query.strip()
    if not q:
        return []
    pattern = f"%{q}%"
    rows = (
        db.query(Occurrence, Page, Document)
        .join(Page, Page.id == Occurrence.page_id)
        .join(Document, Document.id == Occurrence.document_id)
        .filter(
            Occurrence.term_type.in_(
                ["scientific_name", "scientific_name_abbrev"]
            ),
            Occurrence.term.ilike(pattern),
        )
        .order_by(Occurrence.confidence.desc(), Page.page_number.asc())
        .limit(limit)
        .all()
    )
    out: List[SearchResultItem] = []
    seen: set[tuple] = set()
    for occ, page, doc in rows:
        key = (doc.id, page.page_number, occ.term)
        if key in seen:
            continue
        seen.add(key)
        ctx = occ.context or _context_around(page.text, occ.term)[0]
        out.append(
            SearchResultItem(
                document_id=doc.id,
                document_title=doc.title or doc.file_name,
                file_name=doc.file_name,
                page_number=page.page_number,
                matched_term=occ.term,
                context=ctx,
                score=float(occ.confidence or 1.0),
                match_type="scientific_name",
                viewer_url=_viewer_url(doc.id, page.page_number, occ.term, "scientific"),
            )
        )
    return out


# --------------------------------------------------------------------------- #
# Full-text search via FTS5
# --------------------------------------------------------------------------- #
def _fts_query_safe(q: str) -> str:
    """Build a safe FTS5 MATCH expression.

    Strategy:
      * Treat the whole query as one phrase if it contains any non-ASCII
        characters (CJK etc.) — combined with the trigram tokenizer this
        gives substring-style matching.
      * For pure ASCII queries, split on whitespace, keep word/numeric
        tokens, quote each, and AND them together.
    """
    q = q.strip()
    if not q:
        return ""
    # Escape any embedded double quotes the FTS5 way (double them up).
    cleaned = q.replace('"', '""')
    has_non_ascii = any(ord(c) > 127 for c in cleaned)
    if has_non_ascii:
        return f'"{cleaned}"'
    tokens = re.findall(r"\w+", cleaned, flags=re.UNICODE)
    if not tokens:
        return ""
    return " ".join(f'"{t}"' for t in tokens)


def search_fulltext(
    db: Session, query: str, limit: int = 50
) -> List[SearchResultItem]:
    q = query.strip()
    if not q:
        return []

    # Non-SQLite backends (e.g. SQL Server in production) don't have FTS5;
    # fall back to substring scan, which still gives sensible results.
    if not IS_SQLITE:
        return _fulltext_like_fallback(db, q, limit=limit)

    # Trigram tokenizer can't index queries shorter than 3 characters; fall
    # back to a substring scan so short CJK queries (e.g. "茶树") still work.
    has_non_ascii = any(ord(c) > 127 for c in q)
    if has_non_ascii and len(q) < 3:
        return _fulltext_like_fallback(db, q, limit=limit)

    fts_q = _fts_query_safe(q)
    if not fts_q:
        return []

    with raw_sqlite() as conn:
        try:
            rows = conn.execute(
                """
                SELECT page_id, document_id, page_number,
                       snippet(pages_fts, 3, '<<', '>>', '...', 24) AS snip,
                       bm25(pages_fts) AS rank
                FROM pages_fts
                WHERE pages_fts MATCH ?
                ORDER BY rank ASC
                LIMIT ?
                """,
                (fts_q, limit),
            ).fetchall()
        except Exception as e:
            logger.warning("FTS query failed for %r: %s", fts_q, e)
            return []

    if not rows:
        return []
    doc_ids = list({r["document_id"] for r in rows})
    docs = {d.id: d for d in db.query(Document).filter(Document.id.in_(doc_ids)).all()}

    results: List[SearchResultItem] = []
    # Lower BM25 = better match. Convert to a positive 0..1-ish score.
    ranks = [r["rank"] for r in rows]
    if ranks:
        rmin, rmax = min(ranks), max(ranks)
        rspread = (rmax - rmin) or 1.0

    for r in rows:
        doc = docs.get(r["document_id"])
        if not doc:
            continue
        score = 1.0 - ((r["rank"] - rmin) / rspread) if rows else 0.5
        score = max(0.05, min(1.0, score))
        snip = (r["snip"] or "").replace("\n", " ")
        results.append(
            SearchResultItem(
                document_id=doc.id,
                document_title=doc.title or doc.file_name,
                file_name=doc.file_name,
                page_number=r["page_number"],
                matched_term=q,
                context=snip,
                score=round(score, 4),
                match_type="fulltext",
                viewer_url=_viewer_url(doc.id, r["page_number"], q, "fulltext"),
            )
        )
    return results


def _fulltext_like_fallback(
    db: Session, q: str, limit: int = 50
) -> List[SearchResultItem]:
    """Substring scan over page text — used when the FTS tokenizer can't
    handle very short CJK queries."""
    pattern = f"%{q}%"
    rows = (
        db.query(Page, Document)
        .join(Document, Document.id == Page.document_id)
        .filter(Page.text.ilike(pattern))
        .order_by(Page.document_id.asc(), Page.page_number.asc())
        .limit(limit)
        .all()
    )
    out: List[SearchResultItem] = []
    for page, doc in rows:
        ctx, _ = _context_around(page.text, q)
        out.append(
            SearchResultItem(
                document_id=doc.id,
                document_title=doc.title or doc.file_name,
                file_name=doc.file_name,
                page_number=page.page_number,
                matched_term=q,
                context=ctx,
                score=0.5,
                match_type="fulltext",
                viewer_url=_viewer_url(doc.id, page.page_number, q, "fulltext"),
            )
        )
    return out


# --------------------------------------------------------------------------- #
# Semantic search via chunk embeddings
# --------------------------------------------------------------------------- #
def search_semantic(
    db: Session, query: str, limit: int = 30
) -> Tuple[List[SearchResultItem], Optional[str]]:
    q = query.strip()
    if not q:
        return [], None

    # Build chunk matrix
    chunks = (
        db.query(Chunk).filter(Chunk.embedding.isnot(None)).all()
    )
    if not chunks:
        return [], "no_embeddings"

    qv = embedding_service.embed_query(q)
    if qv is None:
        return [], "embeddings_unavailable"

    matrix = np.vstack(
        [np.frombuffer(c.embedding, dtype=np.float32) for c in chunks]
    )
    idx, sims = embedding_service.cosine_topk(qv, matrix, k=limit)
    if len(idx) == 0:
        return [], None

    page_ids = list({chunks[i].page_id for i in idx})
    pages = {p.id: p for p in db.query(Page).filter(Page.id.in_(page_ids)).all()}
    doc_ids = list({p.document_id for p in pages.values()})
    docs = {d.id: d for d in db.query(Document).filter(Document.id.in_(doc_ids)).all()}

    results: List[SearchResultItem] = []
    seen_pages: set[Tuple[int, int]] = set()
    for j, sim in zip(idx, sims):
        chunk = chunks[int(j)]
        page = pages.get(chunk.page_id)
        if not page:
            continue
        doc = docs.get(page.document_id)
        if not doc:
            continue
        key = (doc.id, page.page_number)
        if key in seen_pages:
            continue
        seen_pages.add(key)
        ctx = chunk.text[:240].replace("\n", " ")
        results.append(
            SearchResultItem(
                document_id=doc.id,
                document_title=doc.title or doc.file_name,
                file_name=doc.file_name,
                page_number=page.page_number,
                matched_term=q,
                context=ctx,
                score=round(float(sim), 4),
                match_type="semantic",
                viewer_url=_viewer_url(doc.id, page.page_number, q, "semantic"),
            )
        )
    return results, None


# --------------------------------------------------------------------------- #
# Hybrid: combine fulltext + semantic + scientific, sum normalised scores.
# --------------------------------------------------------------------------- #
def search_hybrid(
    db: Session, query: str, limit: int = 50
) -> Tuple[List[SearchResultItem], Optional[str]]:
    fulltext = search_fulltext(db, query, limit=limit)
    scientific = search_scientific(db, query, limit=limit)
    semantic, sem_note = search_semantic(db, query, limit=limit)

    bucket: Dict[Tuple[int, int], SearchResultItem] = {}

    def merge(results: List[SearchResultItem], weight: float) -> None:
        for r in results:
            key = (r.document_id, r.page_number)
            existing = bucket.get(key)
            new_score = r.score * weight
            if existing is None:
                merged = r.model_copy()
                merged.score = round(new_score, 4)
                merged.match_type = r.match_type
                bucket[key] = merged
            else:
                # Combine: pick the longer/most specific term/context, sum scores.
                merged = existing
                merged.score = round(min(1.0, existing.score + new_score), 4)
                if len(r.context) > len(existing.context):
                    merged.context = r.context
                if r.match_type == "scientific_name" and existing.match_type != "scientific_name":
                    merged.matched_term = r.matched_term
                    merged.match_type = "hybrid"
                elif existing.match_type != r.match_type:
                    merged.match_type = "hybrid"

    merge(scientific, 0.6)
    merge(fulltext, 0.5)
    merge(semantic, 0.6)

    items = list(bucket.values())
    items.sort(key=lambda x: x.score, reverse=True)
    items = items[:limit]
    for it in items:
        it.viewer_url = _viewer_url(it.document_id, it.page_number, query, "hybrid")
    return items, sem_note


def search(
    db: Session, query: str, mode: str, limit: int = 50
) -> Tuple[List[SearchResultItem], Optional[str]]:
    mode = (mode or "").lower().strip()
    if mode == "exact":
        return search_exact(db, query, limit=limit), None
    if mode in {"scientific", "scientific_name"}:
        return search_scientific(db, query, limit=limit), None
    if mode == "fulltext":
        return search_fulltext(db, query, limit=limit), None
    if mode == "semantic":
        return search_semantic(db, query, limit=limit)
    if mode == "hybrid":
        return search_hybrid(db, query, limit=limit)
    # default: hybrid
    return search_hybrid(db, query, limit=limit)
