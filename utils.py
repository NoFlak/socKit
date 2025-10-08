"""Shared utility helpers for the socKit platform."""

from __future__ import annotations

import os
import platform
from pathlib import Path

from command_utils import execute_command
from config import load_config
from logging_utils import log_table, write_action


def create_directory(path: str) -> None:
    target = Path(path)
    try:
        target.mkdir(parents=True, exist_ok=True)
        write_action("Directory ensured.", context={"path": str(target)})
        print(f"[INFO] Directory ready at {target}")
    except OSError as exc:
        print(f"[ERROR] Unable to create directory at {target}: {exc}")
        write_action("Directory creation failed.", level="ERROR", context={"path": str(target), "error": str(exc)})


def list_directory_contents(path: str = ".") -> None:
    target = Path(path)
    try:
        if not target.exists():
            raise FileNotFoundError(f"{target} does not exist")
        entries = sorted(target.iterdir(), key=lambda p: (p.is_file(), p.name.lower()))
        print("\n=== Directory Contents ===")
        rows = []
        for entry in entries:
            entry_type = "DIR" if entry.is_dir() else "FILE"
            size = entry.stat().st_size if entry.is_file() else "-"
            print(f"{entry_type:>4}  {entry.name}")
            rows.append((entry_type, entry.name, size))
        log_table("directory_listing", ("type", "name", "size"), rows)
        write_action("Directory contents listed.", context={"path": str(target), "entries": len(rows)})
    except OSError as exc:
        print(f"[ERROR] Unable to list directory {target}: {exc}")
        write_action("Directory listing failed.", level="ERROR", context={"path": str(target), "error": str(exc)})


def display_ip_configuration(interface_hint: str | None = None) -> None:
    os_name = platform.system()
    if os_name == "Windows":
        command = "ipconfig /all"
    elif os_name == "Darwin":
        command = "ifconfig"
    else:
        command = "ip address show"
    context = {"interface_hint": interface_hint} if interface_hint else None
    execute_command(command, "IP Configuration", timeout=120)
    write_action("Displayed IP configuration.", context=context or {})


def display_mac_addresses() -> None:
    os_name = platform.system()
    if os_name == "Windows":
        command = "getmac"
    else:
        command = "ip link show"
    execute_command(command, "MAC Address Information", timeout=120)
    write_action("Displayed MAC addresses.")


def display_user_information() -> None:
    config = load_config()
    try:
        username = os.getenv("USERNAME") or os.getenv("USER") or "unknown"
        domain = os.getenv("USERDOMAIN") or os.getenv("DOMAIN") or "N/A"
        computer = os.getenv("COMPUTERNAME") or platform.node()
        print("\n=== User Information ===")
        print(f"User Name   : {username}")
        print(f"User Domain : {domain}")
        print(f"Computer    : {computer}")
        write_action(
            "Displayed user information.",
            context={"user": username, "domain": domain, "computer": computer, "log_folder": config.log_folder},
        )
    except OSError as exc:
        print(f"[ERROR] Unable to read user information: {exc}")
        write_action("User information lookup failed.", level="ERROR", context={"error": str(exc)})