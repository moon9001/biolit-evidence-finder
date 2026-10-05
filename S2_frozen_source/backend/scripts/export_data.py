"""Export all documents, pages, occurrences and search logs as a single
JSON snapshot. Works on both SQLite and SQL Server backends.

Usage:
    python scripts/export_data.py                # writes to ./biolit_export.json
    python scripts/export_data.py path/to/out.json
"""
from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE.parent))

from app.database import SessionLocal  # noqa: E402
from app.models import Chunk, Document, Occurrence, Page, SearchLog  # noqa: E402


def _row_to_dict(obj):
    out = {}
    for col in obj.__table__.columns:
        val = getattr(obj, col.name)
        if isinstance(val, datetime):
            out[col.name] = val.isoformat()
        elif isinstance(val, bytes):
            out[col.name] = f"<binary {len(val)} bytes>"
        else:
            out[col.name] = val
    return out


def main() -> int:
    out_path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("biolit_export.json")

    with SessionLocal() as db:
        docs = [_row_to_dict(d) for d in db.query(Document).all()]
        pages = [_row_to_dict(p) for p in db.query(Page).all()]
        occs = [_row_to_dict(o) for o in db.query(Occurrence).all()]
        chunks = [_row_to_dict(c) for c in db.query(Chunk).all()]
        logs = [_row_to_dict(s) for s in db.query(SearchLog).all()]

    payload = {
        "exported_at": datetime.utcnow().isoformat() + "Z",
        "counts": {
            "documents": len(docs),
            "pages": len(pages),
            "occurrences": len(occs),
            "chunks": len(chunks),
            "search_logs": len(logs),
        },
        "documents": docs,
        "pages": pages,
        "occurrences": occs,
        "chunks": chunks,
        "search_logs": logs,
    }

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    print(f"Wrote {out_path.resolve()}")
    print("Counts:", payload["counts"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
