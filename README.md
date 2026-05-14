# BioLitEvidence Finder

Page-level evidence discovery for biodiversity literature.

BioLitEvidence Finder ingests PDF documents — taxonomic monographs, regional
floras, plant atlases, and journal articles — and builds a searchable index
of every page. It identifies Latin binomials, Chinese plant names,
locality terms and topical keywords, then lets researchers search by
keyword, scientific name, or natural-language question. **Every result
links back to the exact page** so claims can be verified against the
original source.

The system is written for **page-level evidence retrieval**, not
generative answering: results always carry a document, a page number, an
extracted match, and a context snippet.

---

## Highlights

- **Five search modes**: exact, scientific name, full-text (FTS5), semantic
  (embedding similarity), and hybrid combining all of them.
- **Per-page evidence**: every hit includes the page image, the page text,
  the matched term, a context snippet, and a deep link to the original PDF
  with `#page=N` so the browser jumps straight to that page.
- **Bilingual UI**: the interface defaults to English and can be switched
  to Chinese with one click in the top-right corner.
- **Offline-first**: works without any external services. LLM and
  embedding APIs are optional accelerators; rule-based extraction and
  full-text search remain available without them.
- **OpenAI-compatible APIs**: any chat / embedding endpoint that follows
  the OpenAI API shape can be plugged in (e.g. DeepSeek, Qwen, OpenAI,
  Azure OpenAI, local vLLM).
- **Pluggable OCR**: optional pytesseract for scanned pages.

---

## Quick start (one click)

After cloning the repository:

| Platform | Command |
|----------|---------|
| Windows  | double-click `start.bat` |
| Linux / macOS | `bash start.sh` |

The first run installs the Python virtual environment and the npm
dependencies, then starts both servers. Open
**http://localhost:5173** in a browser. The interface defaults to
English; click **中文** in the header to switch language.

Requirements on the host:

- Python **3.11+**
- Node.js **18+**
- (optional) Tesseract OCR with `chi_sim` language pack, only needed for
  scanned PDFs

---

## Manual setup

### Backend

```bash
cd backend
python -m venv .venv
# Windows
.venv\Scripts\activate
# Linux / macOS
source .venv/bin/activate

pip install -r requirements.txt
cp .env.example .env       # then edit .env to add API keys (optional)

uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Swagger UI: **http://localhost:8000/docs**

### Frontend

```bash
cd frontend
npm install
npm run dev -- --host 0.0.0.0 --port 5173
```

Open **http://localhost:5173**.

The Vite dev server proxies `/api/*` to `http://127.0.0.1:8000`, so the
two processes work together as long as both are running locally.

### Production build (frontend)

```bash
cd frontend
npm run build       # outputs to frontend/dist/
```

Serve `frontend/dist/` with any static web server (nginx, Caddy, etc.)
and reverse-proxy `/api/*` to the backend.

---

## Configuration

All configuration is read from `backend/.env`. A complete example lives
at `backend/.env.example`. The minimum useful configuration is empty —
the system runs in offline mode with rule-based extraction and full-text
search.

### LLM (optional, for richer keyword extraction)

```env
LLM_API_BASE_URL=https://api.deepseek.com
LLM_API_KEY=sk-...
LLM_MODEL=deepseek-v4-flash
```

Any OpenAI-compatible endpoint works. The system asks the model to
extract structured metadata (scientific names, Chinese names, locations,
keywords, evidence type) from each page and validates every returned
entry against the page text to guard against fabrication.

### Embedding (optional, for semantic search)

```env
EMBEDDING_API_BASE_URL=https://uni-api.cstcloud.cn/v1
EMBEDDING_API_KEY=sk-...
EMBEDDING_MODEL=qwen3-embedding:8b
```

If no embedding API is configured, the system tries
`sentence-transformers` locally (`pip install sentence-transformers`).
If neither is available, semantic search is disabled and the other four
search modes still work.

### Database

The default database is a single SQLite file at `data/app.db`. SQLite
with FTS5 trigram tokenizer handles bilingual full-text search well and
keeps the project zero-config for new users.

To use a different database (PostgreSQL, MySQL, SQL Server, etc.), set
`DATABASE_URL` in `.env` to a SQLAlchemy connection string, for
example:

```env
DATABASE_URL=postgresql+psycopg://user:pass@host/biolit
```

The full-text mode automatically falls back to a SQL `LIKE` scan on
non-SQLite backends; the four other search modes are unchanged.

### Storage paths

```env
DATA_DIR=../data
DB_PATH=../data/app.db
PAGE_IMAGE_DPI=144
```

`data/uploads/` holds the original PDFs, `data/page_images/` holds the
rendered page screenshots used in the viewer.

---

## Optional: install Tesseract OCR

For scanned PDFs without a text layer.

| Platform | Command |
|----------|---------|
| Debian/Ubuntu | `sudo apt-get install tesseract-ocr tesseract-ocr-chi-sim` |
| macOS (Homebrew) | `brew install tesseract tesseract-lang` |
| Windows | Install from <https://github.com/UB-Mannheim/tesseract/wiki> and add `tesseract.exe` to PATH |

If Tesseract is not present, the system processes text-layer PDFs
normally and silently skips OCR for scanned pages.

---

## Using the application

The companion document **[USER_GUIDE.md](./USER_GUIDE.md)** walks through
the typical workflow: upload, monitor processing, search across modes,
view evidence and export results.

---

## Repository layout

```
biolit-evidence-finder/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI entry point
│   │   ├── config.py            # .env-driven settings
│   │   ├── database.py          # SQLAlchemy engine + FTS5 bootstrap
│   │   ├── models.py            # documents / pages / occurrences / chunks
│   │   ├── schemas.py           # Pydantic IO schemas
│   │   ├── routers/             # documents / search / settings / stats
│   │   └── services/            # pdf, ocr, extraction, llm, embedding,
│   │                              search, export
│   ├── scripts/                 # demo PDF generator, smoke test,
│   │                              export and reset utilities
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   └── src/
│       ├── pages/               # Dashboard, Upload, Documents, Search,
│       │                          Viewer, Settings
│       ├── components/, api/, types/, i18n/
│       ├── App.tsx, main.tsx, index.css
│       └── ...                  # vite.config.ts, tailwind, tsconfig
├── data/
│   ├── uploads/                 # original PDFs
│   ├── page_images/             # rendered page screenshots
│   └── app.db                   # SQLite database
├── start.bat / start.sh         # one-click launchers
├── docker-compose.yml
├── README.md / USER_GUIDE.md / DEPLOY.md
```

---

## Data management

### Generate a demo PDF

```bash
cd backend
python scripts/create_demo_pdf.py demo.pdf
```

Then upload `demo.pdf` through the UI to verify the full pipeline.

### Export the index as JSON

```bash
cd backend
python scripts/export_data.py            # -> ./biolit_export.json
python scripts/export_data.py /path/out.json
```

The export contains all documents, pages, occurrences, chunks (without
binary embeddings), and search logs. Original PDFs in
`data/uploads/` are not duplicated.

### Reset all data

```bash
cd backend
python scripts/reset_data.py --yes              # wipe everything
python scripts/reset_data.py --yes --backup     # export to JSON first
```

This clears the database tables and the FTS5 index, then removes files
under `data/uploads/` and `data/page_images/`. The schema is recreated
automatically on the next backend start.

---

## API reference

Interactive Swagger UI: **http://localhost:8000/docs**

Selected endpoints:

```
GET  /api/health
GET  /api/stats
GET  /api/settings/status

POST   /api/documents/upload                  # multipart files=
GET    /api/documents
GET    /api/documents/{id}
DELETE /api/documents/{id}
POST   /api/documents/{id}/process            # re-process a document

GET  /api/documents/{id}/pages
GET  /api/documents/{id}/pages/{page_number}
GET  /api/documents/{id}/file
GET  /api/documents/{id}/page-image/{page_number}

GET  /api/search?q=...&mode=exact|scientific|fulltext|semantic|hybrid&limit=
GET  /api/export/search-results?q=...&mode=...&format=csv|json
```

A typical search response:

```json
{
  "query": "Camellia sinensis",
  "mode": "scientific",
  "result_count": 2,
  "results": [
    {
      "document_id": 1,
      "document_title": "Flora of China — Theaceae.pdf",
      "file_name": "Flora of China — Theaceae.pdf",
      "page_number": 235,
      "matched_term": "Camellia sinensis",
      "context": "... Camellia sinensis (L.) Kuntze 茶树 ...",
      "score": 0.85,
      "match_type": "scientific_name",
      "viewer_url": "/viewer/1?page=235&q=Camellia%20sinensis&mode=scientific"
    }
  ]
}
```

---

## Citation

If you use BioLitEvidence Finder in your research, please cite the
accompanying publication. A `CITATION.cff` will be added with the formal
release.

---

## License

Released under the MIT License (see `LICENSE`).
