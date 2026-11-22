"""Portable result exports; secret keys are never serialized."""

import csv
import io
import json
import os
from pathlib import Path

from .hasher import Result


def serialize(results: list[Result], format: str = "json",
              base_dir: Path | None = None) -> str:
    """Serialize results; sum output requires one ordinary file hash algorithm."""
    rows = [{"file": r.source, "size": r.size, "algorithm": r.label,
             "hash": r.formatted(), "base64": r.formatted("base64"),
             "decimal": r.formatted("decimal")} for r in results]
    if format == "json":
        return json.dumps(rows, indent=2, ensure_ascii=False) + "\n"
    if format == "csv":
        stream = io.StringIO(newline="")
        writer = csv.DictWriter(stream, fieldnames=("file", "size", "algorithm", "hash", "base64", "decimal"))
        writer.writeheader()
        writer.writerows(rows)
        return stream.getvalue()
    if format == "sum":
        if not results or len({r.algorithm for r in results}) != 1:
            raise ValueError("Checksum manifests require exactly one algorithm.")
        if any(r.is_hmac or r.checksum or r.source == "Text" for r in results):
            raise ValueError("Checksum manifests require ordinary file hashes, without HMAC.")
        lines = []
        for r in results:
            filename = os.path.relpath(r.source, base_dir) if base_dir else r.source
            filename = Path(filename).as_posix()
            escaped = any(c in filename for c in "\\\n\r")
            filename = filename.replace("\\", "\\\\").replace("\n", "\\n").replace("\r", "\\r")
            prefix = "\\" if escaped else ""
            lines.append(f"{prefix}{r.formatted()}  {filename}\n")
        return "".join(lines)
    if format == "txt":
        return "\n".join(f"{r.label}: {r.formatted()}  {r.source}" for r in results) + "\n"
    raise ValueError(f"Unsupported export format: {format}")


def save_results(path: str | Path, results: list[Result], format: str) -> None:
    """Save UTF-8 results with portable line endings."""
    path = Path(path)
    content = serialize(results, format, path.resolve().parent)
    with path.open("w", encoding="utf-8", newline="") as stream:
        stream.write(content)
