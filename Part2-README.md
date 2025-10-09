# Part 2 - Workflow Handlers & Artifact Store (In Progress)

Phase 2 builds on the data-driven menu foundation by adding safe workflow handlers, artifact storage plumbing, and guard rails to keep generated content intact.

## What's included
- `playbooks/handlers.py` - dry-run-first wrappers for nmap, osquery, tcpdump, and winget preview, all wired into `workflow_engine.bootstrap_builtin_tasks`.
- `utils/artifact_store.py` - local/remote (stubbed S3) artifact store facade automatically invoked by `write_artifact`.
- `playbooks/examples/red_emulation_safe.yml` - red team emulation sample with `exercise: true` and dry-run defaults.
- `menus/menu.yml` - updated Tools Hub and workflows exposing the playbook handlers with safe lab defaults.
- Validation and CI:
  - `scripts/validate_repo.sh` orchestrates bytecode/placeholder checks.
  - `tools/validate_tools.py` verifies PLACEHOLDER tokens and ensures system repair stubs exist when needed.
  - `.githooks/prevent_placeholder_deletion.sh` blocks accidental removal of sentinel tokens.
  - `ci/validate_phase1_to_phase2.yml` GitHub Action runs validation, pytest, and generator dry runs.

## How to exercise
1. Bootstrap tasks (once per session): `python -c "import workflow_engine; workflow_engine.bootstrap_builtin_tasks()"`.
2. Run the dry-run handlers directly, for example:
   ```bash
   python -c "from playbooks.handlers import nmap_top_ports; print(nmap_top_ports(target='lab-host'))"
   ```
3. Execute the safe red team playbook:
   ```bash
   python playbooks/run_playbook.py playbooks/examples/red_emulation_safe.yml --dry-run
   ```

## Validation checklist
- `python tools/validate_tools.py --check-placeholders --ensure-system-tasks`
- `bash scripts/validate_repo.sh`
- `pytest`
- `python tools/generate_menus.py --dry-run`

## Next steps (Phase 2+)
- Expand artifact store to perform real S3/MinIO uploads when credentials are supplied.
- Add richer parsing for nmap/osquery outputs with artifact schema alignment.
- Wire handlers into the AutoMenu PowerShell/Python shims and interactive UI.
