from __future__ import annotations

"""
Safe playbook handlers used by Phase 2 automation workflows.

Each handler defaults to dry-run mode and records intent through the
artifact pipeline so operators can review commands before enabling
live execution in lab environments.
"""

import json
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from logging_utils import write_action
from utils.artifact_store import ArtifactStoreConfig, get_store
from utils.write_artifact import write_artifact

DEFAULT_BASE = Path("artifacts")
_LOCAL_STORE_CACHE: Dict[Path, Any] = {}


def _ensure_binary(binary: str) -> str:
    path = shutil.which(binary)
    if not path:
        raise RuntimeError(f"Required binary '{binary}' not found in PATH.")
    return path


def _record_artifact(
    *,
    operator: str,
    tool: str,
    summary: Dict[str, Any],
    raw_source: Optional[Path] = None,
    dry_run: bool = True,
    artifact_base: Path | str | None = None,
) -> Dict[str, Any]:
    base = Path(artifact_base) if artifact_base else DEFAULT_BASE
    store = None
    if artifact_base:
        store = _LOCAL_STORE_CACHE.get(base)
        if store is None:
            cfg = ArtifactStoreConfig(mode="local", base_dir=base.resolve())
            store = get_store(cfg)
            _LOCAL_STORE_CACHE[base] = store
    return write_artifact(
        operator=operator,
        tool=tool,
        summary=summary,
        raw_source_path=raw_source,
        dry_run=dry_run,
        base=base,
        store=store,
    )


def nmap_top_ports(
    *,
    target: str,
    top_ports: int = 20,
    binary: str = "nmap",
    extra_args: Optional[Iterable[str]] = None,
    dry_run: bool = True,
    lab_confirm: bool = False,
    operator: str = "unknown",
    artifact_base: Path | str | None = None,
) -> Dict[str, Any]:
    """Preview or execute an nmap top-ports scan."""
    base = Path(artifact_base) if artifact_base else DEFAULT_BASE

    args: List[str] = [
        binary,
        "-Pn",
        "--top-ports",
        str(top_ports),
        target,
        "-oX",
        "-",
    ]
    if extra_args:
        args.extend(list(extra_args))

    summary = {
        "command": args,
        "target": target,
        "top_ports": top_ports,
        "extra_args": list(extra_args or []),
        "dry_run": dry_run,
    }

    if dry_run:
        write_action("nmap top-ports dry run planned.", context=summary)
        return _record_artifact(
            operator=operator,
            tool="nmap_top_ports",
            summary=summary,
            dry_run=True,
            artifact_base=artifact_base,
        )

    if not lab_confirm:
        raise RuntimeError("Refusing to execute nmap scan without lab_confirm=True.")

    binary_path = _ensure_binary(binary)
    exec_args = [binary_path] + args[1:]
    result = subprocess.run(
        exec_args,
        capture_output=True,
        text=True,
        check=False,
    )
    summary.update({"exit_code": result.returncode, "command": exec_args})
    write_action(
        "nmap top-ports executed.",
        context={"target": target, "exit_code": result.returncode},
        detailed_results=result.stdout,
    )
    # Persist stdout as raw artifact
    safe_target = re.sub(r"[^A-Za-z0-9_.-]", "_", target)
    raw_path = base / "raw" / f"nmap_top_ports_{safe_target}.xml"
    raw_path.parent.mkdir(parents=True, exist_ok=True)
    raw_path.write_text(result.stdout, encoding="utf-8")
    return _record_artifact(
        operator=operator,
        tool="nmap_top_ports",
        summary=summary,
        dry_run=False,
        raw_source=raw_path,
        artifact_base=artifact_base,
    )


def osquery_snapshot(
    *,
    query: str = "SELECT * FROM os_version;",
    binary: str = "osqueryi",
    dry_run: bool = True,
    operator: str = "unknown",
    artifact_base: Path | str | None = None,
) -> Dict[str, Any]:
    """Run an osquery snapshot (read-only)."""
    base = Path(artifact_base) if artifact_base else DEFAULT_BASE
    args = [binary, "--json", query]
    summary = {"query": query, "binary": binary, "dry_run": dry_run, "command": args.copy()}

    if dry_run:
        write_action("osquery snapshot dry run planned.", context=summary)
        return _record_artifact(
            operator=operator,
            tool="osquery_snapshot",
            summary=summary,
            dry_run=True,
            artifact_base=artifact_base,
        )

    binary_path = _ensure_binary(binary)
    result = subprocess.run(
        [binary_path, "--json", query],
        capture_output=True,
        text=True,
        check=False,
    )
    payload = {
        "query": query,
        "exit_code": result.returncode,
        "rows": json.loads(result.stdout or "[]"),
    }
    write_action(
        "osquery snapshot executed.",
        context={"query": query, "exit_code": result.returncode},
        detailed_results=result.stdout,
    )
    raw_path = base / "raw" / "osquery_snapshot.json"
    raw_path.parent.mkdir(parents=True, exist_ok=True)
    raw_path.write_text(result.stdout or "[]", encoding="utf-8")
    summary.update(
        {
            "exit_code": result.returncode,
            "row_count": len(payload["rows"]),
            "command": [binary_path] + args[1:],
        }
    )
    return _record_artifact(
        operator=operator,
        tool="osquery_snapshot",
        summary=summary,
        dry_run=False,
        raw_source=raw_path,
        artifact_base=artifact_base,
    )


def winget_preview(
    *,
    include_unknown: bool = True,
    operator: str = "unknown",
    dry_run: bool = True,
    artifact_base: Path | str | None = None,
) -> Dict[str, Any]:
    """Wrapper around the admin winget preview task."""
    from workflow_engine import _winget_upgrade_task

    summary = {
        "include_unknown": include_unknown,
        "dry_run": dry_run,
        "operator": operator,
    }
    if dry_run:
        write_action("winget preview dry run planned.", context=summary)
        return _record_artifact(
            operator=operator,
            tool="winget_preview",
            summary=summary,
            dry_run=True,
            artifact_base=artifact_base,
        )

    preview = _winget_upgrade_task(include_unknown=include_unknown, dry_run=True)
    summary.update({"preview": preview})
    return _record_artifact(
        operator=operator,
        tool="winget_preview",
        summary=summary,
        dry_run=False,
        artifact_base=artifact_base,
    )


def tcpdump_capture(
    *,
    interface: str = "eth0",
    duration: int = 60,
    packet_count: int = 0,
    binary: str = "tcpdump",
    dry_run: bool = True,
    lab_confirm: bool = False,
    operator: str = "unknown",
    artifact_base: Path | str | None = None,
) -> Dict[str, Any]:
    """Capture a tcpdump trace (dry-run by default)."""
    base = Path(artifact_base) if artifact_base else DEFAULT_BASE
    core_args: List[str] = ["-i", interface]
    if packet_count > 0:
        core_args.extend(["-c", str(packet_count)])
    if duration > 0:
        core_args.extend(["-G", str(duration), "-W", "1"])

    summary = {
        "interface": interface,
        "duration": duration,
        "packet_count": packet_count,
        "command": [binary] + core_args,
        "lab_confirm": lab_confirm,
        "dry_run": dry_run,
    }

    if dry_run:
        write_action("tcpdump capture dry run planned.", context=summary)
        return _record_artifact(
            operator=operator,
            tool="tcpdump_capture",
            summary=summary,
            dry_run=True,
            artifact_base=artifact_base,
        )

    if not lab_confirm:
        raise RuntimeError("Refusing to execute tcpdump without lab_confirm=True.")

    binary_path = _ensure_binary(binary)
    safe_iface = re.sub(r"[^A-Za-z0-9_.-]", "_", interface)
    capture_path = base / "raw" / f"tcpdump_capture_{safe_iface}.pcap"
    capture_path.parent.mkdir(parents=True, exist_ok=True)

    cmd = [binary_path, *core_args, "-w", str(capture_path)]

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        check=False,
    )

    summary.update(
        {
            "exit_code": result.returncode,
            "capture_file": str(capture_path),
            "command": [binary] + core_args + ["-w", str(capture_path)],
        }
    )
    write_action(
        "tcpdump capture executed.",
        context={"interface": interface, "exit_code": result.returncode},
        detailed_results=result.stderr,
    )
    return _record_artifact(
        operator=operator,
        tool="tcpdump_capture",
        summary=summary,
        dry_run=False,
        raw_source=capture_path,
        artifact_base=artifact_base,
    )


__all__ = [
    "nmap_top_ports",
    "osquery_snapshot",
    "winget_preview",
    "tcpdump_capture",
]
