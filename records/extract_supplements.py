"""Verify and reconstruct anonymous supplementary bytes into a NEW directory."""
from pathlib import Path, PurePosixPath
import argparse, base64, hashlib, json

def records(path, marker):
    text = Path(path).read_text(encoding="ascii")
    decoder = json.JSONDecoder()
    for index, char in enumerate(text):
        if char != "{":
            continue
        try:
            obj, _ = decoder.raw_decode(text[index:])
        except ValueError:
            continue
        if isinstance(obj, dict) and marker(obj):
            return obj
    raise ValueError("Supplementary payload not found")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--s2", required=True)
    parser.add_argument("--s3", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    s2 = records(args.s2, lambda x: "files" in x and any("BioLitEvidence source supplement v1" in str(v) for v in x.values() if isinstance(v, str)))
    s3 = records(args.s3, lambda x: x.get("record_format") == "AJIM S3 checked anonymous evidence v1")
    pending, seen = [], set()
    for prefix, entries in [("S2_frozen_source", s2["files"]), ("records", s3["record_groups"])]:
        for entry in entries:
            rel = entry.get("path", entry.get("file"))
            p = PurePosixPath(rel)
            if p.is_absolute() or ".." in p.parts or "\\" in rel or ":" in rel or not p.parts:
                raise ValueError("Unsafe source path")
            destination = PurePosixPath(prefix) / p
            if destination.as_posix().casefold() in seen:
                raise ValueError("Duplicate source path")
            seen.add(destination.as_posix().casefold())
            data = base64.b64decode(entry["data_base64"], validate=True)
            if hashlib.sha256(data).hexdigest() != entry["sha256"]:
                raise ValueError("Digest mismatch: " + rel)
            pending.append((destination, data))
    target = Path(args.output).resolve()
    if target.exists():
        raise FileExistsError("Output directory must not already exist")
    for rel, _ in pending:
        if not (target / Path(rel.as_posix())).resolve().is_relative_to(target):
            raise ValueError("Target escapes output directory")
    target.mkdir(parents=True)
    for rel, data in pending:
        output = target / Path(rel.as_posix())
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(data)
    print(json.dumps({"source_files": len(s2["files"]), "record_files": len(s3["record_groups"]), "sha256_verified": len(pending)}))

if __name__ == "__main__":
    main()
