AJIM anonymous replay records

The supplementary DOCX provides the narrative evidence report. The S3 machine
record contains these review-facing records as ASCII JSON plus per-file Base64
bytes and SHA-256 digests. S2 contains the exact 57-file anonymous frozen source.
The historical and current folders refer to distinct execution/inspection rounds.
Source readings were assisted by tools; independent expert validation is not
established. The original and fixed-page samples remain separate throughout.

Reconstruct into a NEW directory using Python 3.12:
  python extract_supplements.py --s2 AJIM_Supplementary_Source_S2.txt --s3 AJIM_S3_Machine_Records.txt --output reconstructed

The utility verifies digests and rejects unsafe or duplicate paths. Its operation
is packaging only; it does not change the research prototype or frozen scripts.

The original replay scripts and input specifications are in reproduce/. Supply
the three complete public PDFs identified by the specifications and verify their
SHA-256 digests before running. This package does not redistribute the PDFs or
page images because redistribution permissions have not been established.
Source links, identifiers, page labels, physical positions and input digests are
retained. These public historical PDFs are not internal platform collection data.

Install the pinned requirements into an isolated dependency directory and run
the unchanged scripts through run_trace_adapter.py as shown in the current
execution records, using a new work directory for each run. The commands there
use portable relative paths; actual private command paths are retained internally.
The exact resolved environment is documented; availability on another operating
system or package index is not claimed. No hosted source repository is asserted.

The adapter enables UTF-8 process execution, observes function calls and closes
and checkpoints the new disposable database. It changes no extraction, indexing,
query, sample selection or retrieval logic. No production service is accessed.

Expected recorded outputs are comparisons to audit, not values to force. Preserve
any new mismatch or execution failure. Results are selected-target page returns,
not estimates of collection-wide precision, recall or expert-validated accuracy.
