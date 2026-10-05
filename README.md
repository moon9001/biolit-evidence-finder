# BioLitEvidence Finder supplementary research prototype

This repository publishes the BioLitEvidence Finder 0.1.0 supplementary prototype,
frozen target specifications, retained machine records, run instructions, and
read-only integrity checks. It is not the complete source code of the iFlora.Book
production system. No production service, internal collection, credentials,
manuscript, title page, signed form, or internal review report is included.

The submission snapshot is identified by tag `ajim-submission-20261006`.
The original source and all retained records are preserved byte for byte.
`FREEZE.json` identifies the payload manifest; `SHA256SUMS.csv` lists the lengths
and SHA-256 digests of exactly 57 source files and 56 machine-record files.
The tag's full commit can be obtained with `git rev-parse ajim-submission-20261006^{}`.

## Directory structure

```
S2_frozen_source/       57 unchanged source files, including the original MIT license
records/               56 unchanged S3 files
  reproduce/           frozen targets, runners, input hashes, dependency lock
  historical/          original protocols, annotations and earlier outputs
  current/             four retained runs from 4 October 2026, not new release runs
SHA256SUMS.csv          frozen payload integrity manifest
FREEZE.json            submission snapshot and manifest digest
tools/verify_release.py read-only hashes, counts and 60 retained-array comparisons
LICENSE                unchanged copy of the prototype MIT license
LICENSE_SCOPE.md        boundaries for code, records and third-party literature
THIRD_PARTY_NOTICES.md  dependency licensing inventory and preservation policy
```

## Obtain and verify the frozen materials

Download this tag's source archive using GitHub's Code or tag page, or clone the
repository and check out `ajim-submission-20261006`. Run from the repository root:

```console
python tools/verify_release.py
```

Python 3.11 or newer is sufficient for this check; it uses only the standard
library. It verifies the manifest digest, all 113 file lengths and SHA-256 digests,
exact file counts, and recomputes 60 comparisons between the retained arrays.
It writes no files and neither downloads source PDFs nor reruns the experiment.
Run this check before installing dependencies or using the prototype.

## Install and run the optional prototype interface

The frozen launchers expect Python 3.11+ and Node.js 18+. From `S2_frozen_source/`,
use `start.bat` on Windows or `bash start.sh` on Linux/macOS. Alternatively:

```console
cd S2_frozen_source/backend
python -m venv .venv
```

Activate `.venv` (`.venv\Scripts\activate` on Windows or
`source .venv/bin/activate` on Linux/macOS), then run:

```console
python -m pip install -r requirements.txt
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

In another terminal:

```console
cd S2_frozen_source/frontend
npm ci
npm run dev -- --host 127.0.0.1 --port 5173
```

Open `http://localhost:5173`. The supplied `backend/.env.example` contains empty
credential fields. An empty configuration supports rule-based operation; optional
OCR, LLM and embedding features are separate paths and were not evaluated by the
retained historical-page experiment. The frozen application README and guides
describe the prototype's broader optional interface; they are not evidence that
every path was evaluated or that production functionality was released.

## Replay instructions and historical record scope

The original sample has 2 volumes, 10 pages and 15 frozen targets: literal returns
14/15, name-index returns 13/15, and 153/153 offset conformance. The extension has
3 volumes, 18 pages and 35 targets: literal returns 32/35, name-index returns
22/35, and 254/254 offset conformance. Report these samples separately. The union
is 3 volumes, 28 distinct pages and 50 targets; these selected pages do not support
a collection-wide success rate or an expert taxonomic accuracy estimate.

The four retained runs are from 4 October 2026. `current` is the original input
package's stage name. This release performs integrity and retained-array checks,
not new PDF experiments, and does not regenerate or overwrite any research result.
Initial candidate readings and annotations were assistant/tool-assisted. The
authors' later confirmation of strings and locators is distinct from expert
taxonomic assessment; historical participation fields remain unchanged.

For a new replay, create a separate virtual environment and install
`records/reproduce/requirements-replay.txt`. The exact original resolved versions
are in `requirements-resolved.lock`; cross-platform install success is not claimed.
Obtain the three full public PDFs listed in the two input specifications, store
them as `<identifier>.pdf` in a separate `public_inputs` directory, and verify their
specified SHA-256 digests. Scans and page images are not redistributed here.
Use new, nonexistent output directories, for example:

```console
python -X utf8 records/reproduce/run_trace_adapter.py records/reproduce/reproduce_baseline.py --source-dir S2_frozen_source --cached-pdf-dir public_inputs --work-dir replay_runs/baseline_a
python -X utf8 records/reproduce/run_trace_adapter.py records/reproduce/run_extension_replay.py --source-dir S2_frozen_source --cached-pdf-dir public_inputs --work-dir replay_runs/extension_a
```

Repeat with new directories for independent B runs. Inspect mismatches rather than
forcing expected outputs. The unchanged runners copy the prototype into disposable
stores, use the existing PDF text layer, disable OCR, LLM and vector computation,
and block network connections during application processing. Input downloads, if
needed, precede that processing. Do not point runs at `records/current` or any
production store. `records/current/execution_commands.json` retains the historical
portable command rendering; adapt source paths to this repository structure.

Frozen records such as `records/README.txt` retain the older TXT-only packaging
instructions and the historically true statement that no hosted repository was
then asserted. For this published snapshot, use this root README and the direct
paths above. The older wording is preserved to retain the records' original hashes.

## License boundaries

The original MIT license applies to the supplied prototype software and its
associated software documentation. It does not automatically license all S3
records, quoted literature, external PDFs, page images, or internal collections.
Third-party packages keep their own licenses; no dependencies are vendored.
See `LICENSE_SCOPE.md` and `THIRD_PARTY_NOTICES.md`. Source links and input hashes
identify external copies but do not grant redistribution permission.
