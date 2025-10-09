# Part 1 — Data‑Driven Menus (Implemented)

This branch adds a safe, data‑driven menu system and generator, with a sample generated AutoMenu and building blocks for future parts.

What’s included
- menus/menu.yml — canonical menu manifest (team‑aligned).
- tools/generate_menus.py — generator with --dry-run and --force; writes AutoMenu.ps1 and AutoMenu.py.
- SystemToolkit/AdminTools/AutoMenu.ps1 — sample generated menu committed for reference (generator can overwrite with --force).
- playbooks/run_playbook.py — ephemeral wrapper that embeds metadata and calls the existing engine.
- utils/write_artifact.py — helper to write canonical artifact JSON and record raw artifact SHA256.
- tests/test_menu_generation.py, tests/test_playbook_dryrun.py — light checks.

How to preview/regenerate
- Dry‑run: `python tools/generate_menus.py --dry-run`
- Generate: `python tools/generate_menus.py --force`

Conventions
- PLACEHOLDER/TODO tokens are preserved by design (do not remove until implemented).
- Generated AutoMenu prints actions; it does not execute tasks — use the Python UI or playbooks to run.

Next parts (suggested)
- Part 2: broader artifact exports in tools (nmap/osquery/tcpdump previews), more examples, and placeholder‑guard CI.
- Part 3: optional UI scaffolding (menu viewer + artifact list) and approvals.

