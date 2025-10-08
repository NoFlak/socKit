#!/usr/bin/env python3
from __future__ import annotations

import argparse
import time
import uuid
from pathlib import Path
from typing import Any

import yaml

from workflow_engine import run_playbook as engine_run


def main() -> None:
    ap = argparse.ArgumentParser(description="Run a playbook with ephemeral copy and metadata")
    ap.add_argument("playbook", help="Path to playbook YAML under playbooks/")
    ap.add_argument("--operator", default="unknown")
    ap.add_argument("--profile", default="")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    src = Path(args.playbook)
    if not src.exists():
        raise SystemExit(f"Playbook {src} not found")

    eph_dir = Path("playbooks") / "ephemeral"
    eph_dir.mkdir(parents=True, exist_ok=True)
    ts = time.strftime("%Y%m%dT%H%M%SZ")
    eph = eph_dir / f"{ts}-{uuid.uuid4().hex}.yml"

    try:
        data: Any = yaml.safe_load(src.read_text(encoding="utf-8")) or {}
    except Exception as exc:
        raise SystemExit(f"Invalid YAML: {exc}")

    meta = {
        "operator": args.operator,
        "profile": args.profile,
        "dry_run": bool(args.dry_run),
        "origin": "agent",
        "ts": ts,
    }
    # Merge metadata under top-level 'metadata'
    if not isinstance(data, dict):
        data = {"metadata": meta, "steps": []}
    else:
        data = {**data, "metadata": {**meta, **(data.get("metadata") or {})}}

    eph.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    result = engine_run(eph, dry_run=args.dry_run)
    # Print a compact summary to stdout
    print({"ephemeral": str(eph), "steps": len(data.get("steps", [])), "dry_run": args.dry_run, "result_count": len(result or [])})


if __name__ == "__main__":
    main()

