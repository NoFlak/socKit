"""Logging utilities for the socKit platform."""

from __future__ import annotations

import csv
import json
import os
from datetime import datetime
from typing import Any, Dict, Iterable, Optional

from config import load_config


def _ensure_log_paths(log_folder: str, log_file: str, detailed_file: str) -> None:
    os.makedirs(log_folder, exist_ok=True)
    for filename in (log_file, detailed_file):
        full_path = os.path.join(log_folder, filename)
        if not os.path.exists(full_path):
            open(full_path, "a", encoding="utf-8").close()


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

    config = load_config() if log_folder is None else None
    log_dir = log_folder or config.log_folder  # type: ignore[union-attr]

    _ensure_log_paths(log_dir, log_file, detailed_file)

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    context = context or {}

    csv_path = os.path.join(log_dir, log_file)
    json_path = os.path.join(log_dir, "ToolkitLog.jsonl")
    detailed_path = os.path.join(log_dir, detailed_file)

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