# BioLitEvidence Finder — User Guide

This guide walks through a typical session: upload a batch of PDFs,
monitor processing, search across modes, view per-page evidence, and
export results.

The interface defaults to English. Switch to Chinese with the **中文 / EN**
button in the top-right corner.

---

## 1. Upload PDFs

1. Open **Upload PDF** from the navigation bar.
2. Click the drop area or drag PDF files into it. Multiple files are
   accepted; there is no enforced size limit.
3. Press **Upload and Start Processing**. A progress bar shows upload
   speed and ETA. When upload completes the page automatically navigates
   to **Documents** so you can watch processing.

## 2. Monitor processing

The **Documents** page lists every PDF together with its status:

- **Pending** — accepted, waiting for the worker.
- **Queued** — accepted, in the worker queue.
- **Processing** — currently being parsed; a per-page progress bar shows
  how many pages are done.
- **Completed** — text and embeddings are ready, the page is searchable.
- **Failed** — an error message is displayed inline; click **Reprocess**
  to try again.

Processing is serialized so a large batch will finish reliably even when
LLM and embedding APIs are configured.

## 3. Search

Open **Search** and pick a mode:

| Mode | When to use |
|------|-------------|
| **Exact Match** | Quick literal lookup of a phrase. |
| **Scientific Name** | Latin binomials, abbreviated genera, infraspecific epithets. |
| **Full-Text (FTS)** | General keyword query in Chinese, English, or mixed. |
| **Semantic** | Natural-language questions, e.g. "茶树在云南的分布". |
| **Hybrid** | Combines all of the above with normalised scoring. Recommended default. |

The result table contains:

- Document name and file name
- Page number
- Matched term and match type (`scientific_name`, `fulltext`, `semantic`, …)
- Relevance score
- Context snippet with the match highlighted
- A **View Source →** link to the page viewer

## 4. View page evidence

The Viewer page shows the rendered page screenshot on the left and the
extracted page text on the right. The query term is highlighted in the
text. Use the prev/next buttons or the page-number input to browse.

The **Open Original PDF** button opens the PDF directly at the same page
using the browser's native PDF viewer (`#page=N`).

## 5. Export results

On the search page click **Export CSV** or **Export JSON** to download
the current result set, including viewer URLs. This is convenient for
preparing supplementary materials or running offline analyses.

---

## Configuration tips

- The **Settings** page shows live status of the LLM, embedding, OCR and
  optional DeepSeek-OCR providers, and lets you update API keys without
  restarting the server (the change applies until restart; permanent
  changes go into `backend/.env`).
- The system runs in offline mode if no APIs are configured. In that
  mode keyword and full-text search remain fully functional; semantic
  search is disabled.
- For scanned PDFs install Tesseract with the `chi_sim` language pack
  (see README). Without it, scanned pages are silently skipped.

---

## Troubleshooting

| Symptom | Resolution |
|---------|------------|
| Upload appears to hang | Large PDFs take time; the upload progress bar stays at 100% while the server saves the file. Wait a few seconds. |
| No search results | Check the document is in **Completed** status; reprocess if needed. |
| OCR off | Install Tesseract; verify `tesseract --version` works in the same shell that launches the backend. |
| "no_embeddings" notice in semantic results | Configure the Embedding API in **Settings** or `backend/.env`. |

---

## Citation

If you use this tool in your research, please cite the accompanying
publication. A formal `CITATION.cff` will accompany the release.
