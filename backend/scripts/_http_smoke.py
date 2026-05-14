"""HTTP-level smoke test against a running uvicorn instance."""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import httpx

BASE = "http://127.0.0.1:8000"


def main() -> int:
    pdf = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("demo.pdf")
    if not pdf.exists():
        print(f"Demo PDF not found: {pdf}")
        return 2

    with httpx.Client(timeout=60.0, trust_env=False) as cli:
        # 1. Upload
        with open(pdf, "rb") as f:
            r = cli.post(
                f"{BASE}/api/documents/upload",
                files={"files": (pdf.name, f, "application/pdf")},
            )
        r.raise_for_status()
        docs = r.json()
        doc_id = docs[0]["id"]
        print("upload OK ->", docs[0]["file_name"], "id=", doc_id)

        # 2. Wait for processing
        for i in range(30):
            d = cli.get(f"{BASE}/api/documents/{doc_id}").json()
            if d["status"] == "completed":
                print(f"processed (pages={d['page_count']})")
                break
            if d["status"] == "failed":
                print("FAILED:", d.get("error"))
                return 1
            time.sleep(1)
        else:
            print("timeout waiting for processing")
            return 1

        # 3. Stats
        s = cli.get(f"{BASE}/api/stats").json()
        print("stats:", s)

        # 4. Search modes
        for mode in ("exact", "scientific", "fulltext", "hybrid"):
            r = cli.get(
                f"{BASE}/api/search",
                params={"q": "Camellia sinensis", "mode": mode, "limit": 5},
            )
            r.raise_for_status()
            data = r.json()
            print(
                f"  [{mode:9s}] {data['result_count']} hits "
                + (f"note={data.get('notes')}" if data.get("notes") else "")
            )
            if data["results"]:
                first = data["results"][0]
                print(
                    f"      p.{first['page_number']} {first['matched_term']!r} "
                    f"viewer={first['viewer_url']}"
                )

        r = cli.get(
            f"{BASE}/api/search",
            params={"q": "茶树", "mode": "fulltext", "limit": 5},
        ).json()
        print(f"  [cn-fts   ] {r['result_count']} hits for 茶树")

        # 5. Page assets
        r = cli.get(f"{BASE}/api/documents/{doc_id}/pages/2")
        r.raise_for_status()
        page = r.json()
        print(f"  page 2: text_length={page['text_length']} ocr_used={page['ocr_used']}")

        r = cli.get(f"{BASE}/api/documents/{doc_id}/page-image/2")
        print(f"  page-image/2: status={r.status_code} bytes={len(r.content)}")

        r = cli.get(f"{BASE}/api/documents/{doc_id}/file")
        print(f"  pdf file: status={r.status_code} bytes={len(r.content)}")

        # 6. Export CSV
        r = cli.get(
            f"{BASE}/api/export/search-results",
            params={"q": "Camellia", "mode": "hybrid", "format": "csv"},
        )
        print(
            f"  export csv: status={r.status_code} "
            f"first_line={r.text.splitlines()[0] if r.text else ''}"
        )

        # 7. Settings status
        r = cli.get(f"{BASE}/api/settings/status").json()
        print("  settings:", json.dumps(r, ensure_ascii=False))

    print("\nHTTP smoke test OK.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
