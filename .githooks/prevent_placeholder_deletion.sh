#!/usr/bin/env bash
set -euo pipefail

python <<'PY'
import subprocess
import sys

targets = [
    "menus/menu.yml",
    "tools/generate_menus.py",
    "SystemToolkit/AdminTools/AutoMenu.ps1",
]

missing = []
for target in targets:
    try:
        content = subprocess.check_output(["git", "show", f":{target}"], text=True)
    except subprocess.CalledProcessError:
        continue
    if "PLACEHOLDER" not in content:
        missing.append(target)

if missing:
    print("Preventing commit: PLACEHOLDER token removed from:", ", ".join(missing), file=sys.stderr)
    sys.exit(1)
PY
