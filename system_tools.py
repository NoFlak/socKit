"""Host diagnostics and automation utilities.

- Runs noisy diagnostics synchronously to avoid interleaving with menus.
- Prints concise summaries while persisting full output to logs/HTML.
"""

from __future__ import annotations

import os
import platform
import shutil
from datetime import datetime
from typing import Dict, Iterable, List
from pathlib import Path
import subprocess

from command_utils import execute_command, execute_command_async
from config import load_config
from logging_utils import log_table, write_action


def _log_dir() -> Path:
    cfg = load_config()
    Path(cfg.log_folder).mkdir(parents=True, exist_ok=True)
    return Path(cfg.log_folder)


def _run_and_capture(command: str, description: str, *, head: int = 40, html_name: str | None = None) -> None:
    """Run a command synchronously, print limited output, and persist full results.

    - Prints only the first `head` lines to keep console readable.
    - Writes full text to DetailedResults via `write_action`.
    - Optionally writes an HTML snapshot to the log folder.
    """
    try:
        completed = subprocess.run(command, shell=True, capture_output=True, text=True, check=False)
        output = completed.stdout or completed.stderr or ""
    except OSError as exc:
        print(f"[ERROR] Unable to start '{description}': {exc}")
        write_action(f"{description} failed to start.", level="ERROR", context={"command": command, "error": str(exc)})
        return

    lines = (output or "").splitlines()
    shown = lines[:head]
    for line in shown:
        print(line)
    if len(lines) > len(shown):
        print(f"[... {len(lines) - len(shown)} more lines suppressed. See logs for full output ...]")

    # Persist full text to detailed log
    write_action(f"{description} completed.", detailed_results=output, context={"command": command, "lines": len(lines)})

    # Optional HTML snapshot
    if html_name:
        log_dir = _log_dir()
        html_path = log_dir / html_name
        try:
            html = [
                "<html><head><meta charset=\"utf-8\"><title>",
                description,
                "</title><style>body{font-family:Segoe UI, Arial, sans-serif} pre{white-space:pre-wrap}</style></head><body>",
                f"<h2>{description}</h2>",
                "<pre>",
                output,
                "</pre>",
                "</body></html>",
            ]
            html_path.write_text("".join(html), encoding="utf-8")
            print(f"[INFO] Full output saved to {html_path}")
            write_action("HTML snapshot written.", context={"path": str(html_path)})
        except OSError as exc:
            print(f"[WARN] Failed to write HTML snapshot: {exc}")
            write_action("HTML snapshot failed.", level="WARNING", context={"error": str(exc)})


def system_file_checker() -> None:
    os_name = platform.system()
    if os_name == "Windows":
        command = "sfc /scannow"
    elif os_name == "Linux":
        command = "sudo fsck -N /"
    elif os_name == "Darwin":
        command = "diskutil verifyVolume /"
    else:
        print("[WARN] System File Checker is not supported on this OS.")
        write_action("System file checker unsupported OS.", level="WARNING", context={"os": os_name})
        return

    print("System File Checker may take several minutes to complete. Please wait...")
    _run_and_capture(command, "System File Checker", head=60)


def collect_system_overview() -> Dict[str, str]:
    """Collect a structured snapshot of high-level host details."""

    os_name = platform.system()
    overview = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "os": os_name,
        "os_release": platform.release(),
        "os_version": platform.version(),
        "architecture": platform.machine(),
        "hostname": platform.node(),
        "processor": platform.processor() or "unknown",
        "python_version": platform.python_version(),
        "working_directory": os.getcwd(),
    }

    try:
        total, used, free = shutil.disk_usage(os.getcwd())
        overview.update(
            {
                "disk_total_gb": f"{total / (1024 ** 3):.2f}",
                "disk_used_gb": f"{used / (1024 ** 3):.2f}",
                "disk_free_gb": f"{free / (1024 ** 3):.2f}",
            }
        )
    except OSError as exc:
        write_action("Disk usage collection failed.", level="WARNING", context={"error": str(exc)})

    write_action("Collected system overview.", context=overview)
    return overview


def display_system_overview() -> None:
    overview = collect_system_overview()
    print("\n=== System Overview ===")
    for key, value in overview.items():
        print(f"{key.replace('_', ' ').title():<24}: {value}")


def enumerate_services() -> None:
    """List system services or daemons based on platform."""

    os_name = platform.system()
    if os_name == "Windows":
        command = "sc query type= service state= all"
        description = "Windows service inventory"
    elif os_name == "Linux":
        command = "systemctl list-units --type=service --all"
        description = "Systemd service inventory"
    elif os_name == "Darwin":
        command = "launchctl list"
        description = "Launchd service inventory"
    else:
        print("[WARN] Service enumeration is not supported on this OS.")
        write_action("Service enumeration unsupported.", level="WARNING", context={"os": os_name})
        return

    # Capture output without streaming the entire list to the console.
    # Save a full HTML snapshot for easy viewing.
    _run_and_capture(command, description, head=60, html_name="service_inventory.html")


def list_critical_paths(paths: Iterable[str] | None = None) -> None:
    """Capture metadata for critical SOC paths to support baselining."""

    default_paths = [
        "/etc/passwd",
        "/etc/shadow",
        "/var/log",
        "C:/Windows/System32",
        "C:/Windows/System32/drivers/etc/hosts",
    ]

    seen: List[tuple[str, str, str]] = []
    for path in paths or default_paths:
        normalized = os.path.expandvars(path)
        exists = os.path.exists(normalized)
        status = "present" if exists else "missing"
        mtime = datetime.fromtimestamp(os.path.getmtime(normalized)).isoformat() if exists else "N/A"
        seen.append((normalized, status, mtime))
        print(f"{normalized} -> {status} (modified {mtime})")

    log_table("critical_path_inventory", ("path", "status", "modified"), seen)
    write_action("Critical path inventory complete.", context={"paths": len(seen)})
