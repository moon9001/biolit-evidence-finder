"""End-to-end smoke test that exercises the processing pipeline + search,
without spinning up uvicorn. Run from the backend directory:

    python scripts/smoke_test.py demo.pdf
"""
from __future__ import annotations

import shutil
import sys
import tempfile
from pathlib import Path

# Allow running as `python scripts/smoke_test.py` from the backend directory
# without setting PYTHONPATH manually.
_HERE = Path(__file__).resolve().parent
_BACKEND_DIR = _HERE.parent
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))


def main() -> int:
    pdf_arg = sys.argv[1] if len(sys.argv) > 1 else "demo.pdf"
    src = Path(pdf_arg)
    if not src.exists():
        print(f"PDF not found: {src}")
        return 2

    # Use a temporary data dir so we don't pollute real state.
    tmp = Path(tempfile.mkdtemp(prefix="biolit_smoke_"))
    import os

    os.environ["DATA_DIR"] = str(tmp)
    os.environ["DB_PATH"] = str(tmp / "smoke.db")

    # Importing here so the env vars take effect.
    from app.config import settings
    from app.database import SessionLocal, init_db
    from app.services import pdf_service, search_service

    print(f"Using temp data dir: {settings.data_dir}")
    init_db()

    # Copy the PDF into uploads/
    target = settings.uploads_dir / src.name
    shutil.copy2(src, target)

    db = SessionLocal()
    try:
        doc = pdf_service.init_document(db, file_name=src.name, stored_path=target)
        doc_id = doc.id
        print(f"Initialized document #{doc_id} ({src.name}, {doc.page_count} pages)")
    finally:
        db.close()

    # Run the pipeline synchronously, with LLM disabled (safer for offline test)
    pdf_service.process_document(doc_id, use_llm=False)

    db = SessionLocal()
    try:
        from app.models import Document, Occurrence, Page

        d = db.get(Document, doc_id)
        page_count = db.query(Page).filter(Page.document_id == doc_id).count()
        occ_count = db.query(Occurrence).filter(Occurrence.document_id == doc_id).count()
        print(f"Document status: {d.status} | pages={page_count} | occurrences={occ_count}")
        if d.error:
            print(f"  error: {d.error}")

        sci = (
            db.query(Occurrence)
            .filter(
                Occurrence.document_id == doc_id,
                Occurrence.term_type.in_(["scientific_name", "scientific_name_abbrev"]),
            )
            .limit(10)
            .all()
        )
        print("Scientific names found:")
        for o in sci:
            print(f"  - {o.term} (page_id={o.page_id}, conf={o.confidence:.2f})")

        # Try various search modes
        for mode in ["exact", "scientific", "fulltext", "hybrid"]:
            res, note = search_service.search(db, "Camellia sinensis", mode, limit=5)
            print(
                f"[{mode:9s}] {len(res)} hits"
                + (f" note={note}" if note else "")
            )
            for r in res[:3]:
                print(
                    f"   p.{r.page_number} score={r.score:.3f} type={r.match_type} "
                    f"term={r.matched_term!r}"
                )
                print(f"      {r.context[:120]}...")

        # Chinese-only query via FTS
        res, note = search_service.search(db, "茶树", "fulltext", limit=5)
        print(f"[fulltext-cn] {len(res)} hits for '茶树'")
        for r in res[:3]:
            print(f"   p.{r.page_number}: {r.context[:120]}")

    finally:
        db.close()

    print("\nSmoke test OK.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
