#!/usr/bin/env bash
set -euo pipefail

echo "[validate_repo] Repository checklist starting."

python -m compileall main.py workflow_engine.py playbooks || {
  echo "[validate_repo] Bytecode compilation failed." >&2
  exit 1
}

python tools/validate_tools.py --check-placeholders --ensure-system-tasks

echo "[validate_repo] Checklist complete."
