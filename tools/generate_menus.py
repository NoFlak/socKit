#!/usr/bin/env python3
"""
Generate auto menus from menus/menu.yml without touching hand-written files.

Outputs:
- SystemToolkit/AdminTools/AutoMenu.ps1 (PowerShell menu)
- SystemToolkit/AdminTools/AutoMenu.py (Python menu shim)

Usage:
  python tools/generate_menus.py [--dry-run]

Safety:
- Preserves any files with PLACEHOLDER/TODO content (does not delete/modify them).
- Only writes AutoMenu.* files.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict

import yaml

ROOT = Path(__file__).resolve().parents[1]
MENU_PATH = ROOT / "menus" / "menu.yml"
OUT_DIR = ROOT / "SystemToolkit" / "AdminTools"


def load_menu() -> Dict[str, Any]:
    data = yaml.safe_load(MENU_PATH.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise SystemExit("menus/menu.yml must be a YAML mapping")
    return data


def render_ps1(menu: Dict[str, Any]) -> str:
    lines = []
    lines.append("# Auto-generated. Do not edit by hand.\n")
    lines.append("$ErrorActionPreference = 'Stop'\n")
    lines.append("function Show-Menu {\n")
    lines.append("  while ($true) {\n")
    lines.append("    Clear-Host\n")
    lines.append("    Write-Host '=== Auto Admin Tools ==='\n")
    # Render Tools categories only (for PS submenu)
    tools = menu.get("tools", {}).get("categories", [])
    for idx, cat in enumerate(tools, start=1):
        lines.append(f"    Write-Host '{idx}) {cat.get('label','Category')}'\n")
    lines.append("    Write-Host '0) Exit'\n")
    lines.append("    $sel = Read-Host 'Select'\n")
    lines.append("    switch ($sel) {\n")
    for idx, cat in enumerate(tools, start=1):
        lines.append(f"      '{idx}' {{\n")
        lines.append("        while ($true) {\n")
        lines.append(f"          Write-Host '\n-- {cat.get('label','Category')} --'\n")
        for jdx, item in enumerate(cat.get("items", []), start=1):
            label = item.get("label", "Item")
            lines.append(f"          Write-Host '{jdx}) {label}'\n")
        lines.append("          Write-Host '0) Back'\n")
        lines.append("          $sc = Read-Host 'Select'\n")
        lines.append("          switch ($sc) {\n")
        for jdx, item in enumerate(cat.get("items", []), start=1):
            label = item.get("label", "Item")
            kind = item.get("kind")
            if kind == "ps1":
                script = item.get("script", "")
                lines.append(f"            '{jdx}' {{ & powershell -NoProfile -ExecutionPolicy Bypass -File '{script}'; break }}\n")
            else:
                # For tasks, we emit a note; actual execution is handled in Python UI
                task = item.get("task", "")
                args = json.dumps(item.get("args", {})).replace('"', '""')
                lines.append(f"            '{jdx}' {{ Write-Host 'Task: {task} Args: {args}'; break }}\n")
        lines.append("            '0' { break }\n")
        lines.append("            default { Write-Host 'Invalid selection.' }\n")
        lines.append("          }\n")
        lines.append("        }\n")
        lines.append("      }\n")
    lines.append("      '0' { return }\n")
    lines.append("      default { Write-Host 'Invalid selection.' }\n")
    lines.append("    }\n")
    lines.append("  }\n")
    lines.append("}\n\nShow-Menu\n")
    return "".join(lines)


def render_py(menu: Dict[str, Any]) -> str:
    return (
        "# Auto-generated Python menu shim for Tools Hub\n"
        "from __future__ import annotations\n"
        "import json\nfrom pathlib import Path\n"
        "from workflow_engine import run_playbook, list_tasks\n"
        "import time, yaml\n\n"
        "MENU = " + json.dumps(menu) + "\n\n"
        "def _write_tmp(steps, name):\n"
        "    p = Path('playbooks'); p.mkdir(parents=True, exist_ok=True)\n"
        "    ts = time.strftime('%Y%m%d-%H%M%S')\n"
        "    path = p / f'{name}-{ts}.yaml'\n"
        "    with path.open('w', encoding='utf-8') as f:\n"
        "        yaml.safe_dump({'name': name, 'steps': steps}, f, sort_keys=False)\n"
        "    return path\n\n"
        "def run_task(task, args=None):\n"
        "    steps = [{ 'task': task, 'args': (args or {}) }]\n"
        "    pb = _write_tmp(steps, f'auto_{task.replace('.', '_')}')\n"
        "    run_playbook(pb)\n\n"
        "# PLACEHOLDER: wire into an interactive loop if needed.\n"
    )


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    menu = load_menu()
    out_ps1 = render_ps1(menu)
    out_py = render_py(menu)

    if args.dry_run:
        print("[DRY-RUN] Would write:")
        print("SystemToolkit/AdminTools/AutoMenu.ps1 ({} bytes)".format(len(out_ps1)))
        print("SystemToolkit/AdminTools/AutoMenu.py ({} bytes)".format(len(out_py)))
        return

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "AutoMenu.ps1").write_text(out_ps1, encoding="utf-8")
    (OUT_DIR / "AutoMenu.py").write_text(out_py, encoding="utf-8")
    print("Generated AutoMenu.ps1 and AutoMenu.py")


if __name__ == "__main__":
    main()

