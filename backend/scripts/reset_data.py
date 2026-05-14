"""Wipe all application data: documents, pages, occurrences, chunks,
search logs, FTS5 index, uploaded PDFs and rendered page images.

Requires explicit confirmation:
    python scripts/reset_data.py --yes

Optionally export a JSON snapshot first:
    python scripts/reset_data.py --yes --backup
"""
from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE.parent))

from app.config import settings  # noqa: E402
from app.database import IS_SQLITE, SessionLocal, raw_sqlite  # noqa: E402
from app.models import Chunk, Document, Occurrence, Page, SearchLog  # noqa: E402


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--yes", action="store_true", help="confirm the wipe")
    p.add_argument("--backup", action="store_true",
                   help="export to biolit_export.json before wiping")
    args = p.parse_args()

    if not args.yes:
        print("Refusing to wipe without --yes.")
        return 1

    if args.backup:
        import runpy
        runpy.run_path(str(_HERE / "export_data.py"), run_name="__main__")

    with SessionLocal() as db:
        # Order matters because of foreign keys.
        deleted = {
            "search_logs": db.query(SearchLog).delete(),
            "chunks": db.query(Chunk).delete(),
            "occurrences": db.query(Occurrence).delete(),
            "pages": db.query(Page).delete(),
            "documents": db.query(Document).delete(),
        }
        db.commit()
    print("Deleted rows:", deleted)

    if IS_SQLITE:
        try:
            with raw_sqlite() as conn:
                conn.execute("DELETE FROM pages_fts")
                conn.commit()
            print("Cleared FTS5 index.")
        except Exception as e:
            print(f"FTS5 reset skipped: {e}")

    # Wipe uploaded PDFs and rendered page images.
    for d in (settings.uploads_dir, settings.page_images_dir):
        if d.exists():
            for child in d.iterdir():
                if child.name in (".gitkeep",):
                    continue
                if child.is_file():
                    try:
                        child.unlink()
                    except Exception:
                        pass
                elif child.is_dir():
                    try:
                        shutil.rmtree(child, ignore_errors=True)
                    except Exception:
                        pass
            print(f"Wiped {d}")

    print("\nReset complete.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
