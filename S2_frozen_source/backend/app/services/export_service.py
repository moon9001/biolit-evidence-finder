"""Export search results to CSV / JSON for paper screenshots."""
from __future__ import annotations

import csv
import io
import json
from typing import List

from ..schemas import SearchResultItem


def to_csv(items: List[SearchResultItem]) -> str:
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(
        [
            "document_id",
            "document_title",
            "file_name",
            "page_number",
            "matched_term",
            "match_type",
            "score",
            "context",
            "viewer_url",
        ]
    )
    for it in items:
        writer.writerow(
            [
                it.document_id,
                it.document_title or "",
                it.file_name,
                it.page_number,
                it.matched_term,
                it.match_type,
                it.score,
                it.context,
                it.viewer_url,
            ]
        )
    return buf.getvalue()


def to_json(items: List[SearchResultItem], query: str, mode: str) -> str:
    payload = {
        "query": query,
        "mode": mode,
        "result_count": len(items),
        "results": [it.model_dump() for it in items],
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)
