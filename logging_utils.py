"""Logging utilities for the socKit platform.

Enhancements:
- Secure permissions (best-effort) on log files/dirs when configured.
- Redaction of host/user identifiers when configured.
- Simple retention cleanup for aging log files.
"""

from __future__ import annotations

import csv
import json
import os
from datetime import datetime
from typing import Any, Dict, Iterable, Optional

import platform
import re
from datetime import datetime, timedelta

from config import load_config


def _secure_path(path: str, is_dir: bool) -> None:
    try:
        if os.name != "nt":
            os.chmod(path, 0o700 if is_dir else 0o600)
    except OSError:
        pass


def _ensure_log_paths(log_folder: str, log_file: str, detailed_file: str, *, secure: bool) -> None:
    os.makedirs(log_folder, exist_ok=True)
    if secure:
        _secure_path(log_folder, True)
    for filename in (log_file, detailed_file):
        full_path = os.path.join(log_folder, filename)
        if not os.path.exists(full_path):
            open(full_path, "a", encoding="utf-8").close()
        if secure:
            _secure_path(full_path, False)


def _enforce_retention(log_folder: str, days: int) -> None:
    if days <= 0:
        return
    cutoff = datetime.now() - timedelta(days=days)
    try:
        for name in os.listdir(log_folder):
            if not any(name.endswith(ext) for ext in (".csv", ".jsonl", ".txt", ".html")):
                continue
            full = os.path.join(log_folder, name)
            try:
                mtime = datetime.fromtimestamp(os.path.getmtime(full))
                if mtime < cutoff:
                    os.remove(full)
            except OSError:
                continue
    except OSError:
        pass


def _sanitize(message: str, context: Optional[Dict[str, Any]], detailed: Optional[str], *, enabled: bool) -> tuple[str, Dict[str, Any], Optional[str]]:
    ctx = dict(context or {})
    if not enabled:
        return message, ctx, detailed

    # Redact common identifiers in context
    for key in ("user", "username", "domain", "computer", "hostname", "ip", "mac"):
        if key in ctx and isinstance(ctx[key], str) and ctx[key]:
            ctx[key] = "<redacted>"

    # Patterns: IPv4, MAC, hostnames (simple)
    ipv4 = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")
    mac = re.compile(r"\b([0-9A-Fa-f]{2}[:-]){5}[0-9A-Fa-f]{2}\b")
    host = platform.node()

    def scrub(text: str) -> str:
        text = ipv4.sub("<ip>", text)
        text = mac.sub("<mac>", text)
        if host:
            text = text.replace(host, "<hostname>")
        return text

    msg = scrub(message or "")
    det = scrub(detailed) if isinstance(detailed, str) else detailed
    return msg, ctx, det


def write_action(
    message: str,
    log_folder: Optional[str] = None,
    *,
    level: str = "INFO",
    context: Optional[Dict[str, Any]] = None,
    log_file: str = "ToolkitLog.csv",
    detailed_results: Optional[str] = None,
    detailed_file: str = "DetailedResults.txt",
) -> None:
    """Persist an action entry to both CSV and human-readable logs."""

    cfg = load_config() if log_folder is None else load_config()
    log_dir = log_folder or cfg.log_folder

    _ensure_log_paths(log_dir, log_file, detailed_file, secure=bool(getattr(cfg, "secure_logs", True)))
    _enforce_retention(log_dir, int(getattr(cfg, "log_retention_days", 30)))

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    context = context or {}

    csv_path = os.path.join(log_dir, log_file)
    json_path = os.path.join(log_dir, "ToolkitLog.jsonl")
    detailed_path = os.path.join(log_dir, detailed_file)

    # Sanitize sensitive fields if enabled
    message, context, detailed_results = _sanitize(
        message, context, detailed_results, enabled=bool(getattr(cfg, "redact_host_identifiers", True))
    )

    csv_row = {
        "timestamp": timestamp,
        "level": level.upper(),
        "message": message,
    }
    for key, value in context.items():
        csv_row[str(key)] = value

    try:
        with open(csv_path, "a", newline="", encoding="utf-8") as csv_file:
            writer = csv.DictWriter(csv_file, fieldnames=list(csv_row.keys()))
            if csv_file.tell() == 0:
                writer.writeheader()
            writer.writerow(csv_row)

        json_payload = {"timestamp": timestamp, "level": level.upper(), "message": message, "context": context}
        with open(json_path, "a", encoding="utf-8") as json_file:
            json_file.write(json.dumps(json_payload) + "\n")

        if detailed_results:
            with open(detailed_path, "a", encoding="utf-8") as detail_file:
                detail_file.write(f"\n{timestamp} [{level.upper()}]\n{message}\n{detailed_results}\n")
    except OSError as exc:
        print(f"Error writing log: {exc}")


def log_table(
    title: str,
    headers: Iterable[str],
    rows: Iterable[Iterable[Any]],
    *,
    log_folder: Optional[str] = None,
    log_file: str = "ToolkitTables.csv",
) -> None:
    """Persist a tabular dataset to disk for later analysis."""

    config = load_config() if log_folder is None else None
    log_dir = log_folder or config.log_folder  # type: ignore[union-attr]

    os.makedirs(log_dir, exist_ok=True)
    path = os.path.join(log_dir, log_file)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    try:
        with open(path, "a", newline="", encoding="utf-8") as csv_file:
            writer = csv.writer(csv_file)
            writer.writerow([timestamp, title])
            writer.writerow(list(headers))
            for row in rows:
                writer.writerow(list(row))
            writer.writerow([])
    except OSError as exc:
        print(f"Error writing table log: {exc}")
