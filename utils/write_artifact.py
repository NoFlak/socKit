from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

DEFAULT_BASE = Path("artifacts")


def _ts() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _sha256(path: Path) -> Optional[str]:
    try:
        h = hashlib.sha256()
        with path.open("rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                h.update(chunk)
        return h.hexdigest()
    except OSError:
        return None


def write_artifact(
    *,
    repository: str = "socKit",
    operator: str,
    tool: str,
    tool_version: str = "",
    target: Any = "",
    raw_source_path: Optional[Path] = None,
    summary: Dict[str, Any] | None = None,
    mitre_tags: list[str] | None = None,
    dry_run: bool = True,
    log_path: Optional[str] = None,
    base: Path = DEFAULT_BASE,
) -> Dict[str, Any]:
    """Write canonical artifact JSON under artifacts/json/<ts>/ and copy/move raw if provided.

    Returns the JSON object written. Raw files are expected to be produced by callers; this function
    records their path and SHA256 if present.
    """
    ts = _ts()
    raw_dir = base / "raw" / ts
    json_dir = base / "json" / ts
    raw_dir.mkdir(parents=True, exist_ok=True)
    json_dir.mkdir(parents=True, exist_ok=True)

    raw_rel: Optional[str] = None
    sha: Optional[str] = None
    if raw_source_path and raw_source_path.exists():
        # Keep file in place; record relative path if under repo
        try:
            raw_rel = os.fspath(raw_source_path)
            sha = _sha256(raw_source_path)
        except Exception:
            raw_rel = os.fspath(raw_source_path)

    obj = {
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "repository": repository,
        "operator": operator,
        "tool": tool,
        "tool_version": tool_version,
        "target": target,
        "raw_artifact_path": raw_rel,
        "raw_sha256": sha,
        "summary": summary or {},
        "mitre_tags": mitre_tags or [],
        "dry_run": bool(dry_run),
        "log_path": log_path or "",
    }
    out = json_dir / f"{tool}_{ts}.json"
    out.write_text(json.dumps(obj, indent=2), encoding="utf-8")
    return obj

