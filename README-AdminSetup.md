# AdminSetup Module

AdminSetup is a safety-first PowerShell module that provisions Windows Server roles and Windows Client optional features with guardrails, previews, and logging.

- Safe-by-default (DryRun in production or unless explicitly overridden)
- Idempotent (skips already-present features)
- Gated for risky operations (internet/public profiles require Force + ConfirmOperator)
- Structured logs and JSON summaries written to C:\ProgramData\AdminSetup\artifacts\<ISO8601>\
- CSV-driven flows for multi-target validation and previews

## Quick Start

1) Import the module
```powershell
Import-Module .\AdminSetup\AdminSetup.psm1 -Force
```

2) See available features
```powershell
Get-AvailableTargetFeatures | Sort-Object Target,Name | Format-Table -AutoSize
```

3) Preview an install (DryRun)
```powershell
Install-Features -Feature Web-Server,DNS -DryRun
```

4) Perform a guarded install
```powershell
Install-Features -Feature Web-Server -Force -ConfirmOperator 'BB' -Profile 'rdp-internet'
```

5) Interactive CSV (validate first, then confirm)
- CSV format: `Target,Features,Profile`
- Example row: `SERVER01,DNS;DHCP,server-core`
```powershell
Install-Features -Interactive -CsvPath .\targets.csv -DryRun
# Review the preview output, then:
Install-Features -Interactive -CsvPath .\targets.csv -Force -ConfirmOperator 'BB'
```

## CLI Wrapper

Use the provided script for simple non-destructive runs:
```powershell
.\scripts\install-admin-setup.ps1 --profile server-core --dry-run
.\scripts\install-admin-setup.ps1 --features Web-Server,DNS --confirm-operator BB --force
.\scripts\install-admin-setup.ps1 --targets .\targets.csv --interactive --confirm-operator BB
```

## Admin Tools Submenu (System Toolkit)

Integrate the submenu script into your toolkit launch flow:
- Script: `SystemToolkit\AdminTools\AdminTools.ps1`
- Menu options:
  1) Run AdminSetup (interactive)
  2) Dry-run preview from CSV
  3) Show available features
  4) Upgrade apps with winget (preview then confirm)
  5) Exit

All Admin Tools operations:
- Default to DryRun unless explicitly confirmed
- Require `-Force` and `-ConfirmOperator` for public/internet profiles
- Store run metadata in `SystemToolkit\AdminTools\runs\` for audit

### Playbook Task: Winget Upgrades (Windows)

You can trigger application upgrades via playbooks with a safe preview-first task:

```yaml
steps:
  - task: admin.winget_upgrade
    args:
      include_unknown: true   # optional
      dry_run: true          # preview only (recommended)
```

To perform upgrades, set `dry_run: false` and provide `force: true`:

```yaml
steps:
  - task: admin.winget_upgrade
    args:
      include_unknown: false
      dry_run: false
      force: true
```

## Risk & Safety Defaults

- Network/firewall modifications are never performed automatically. They require:
  - `-Force`, `-ConfirmOperator`, and an explicitly approved `-Profile`
- Production detection defaults to DryRun:
  - Presence of `C:\ProgramData\ProductionFlag` OR domain membership
- All operations are logged with:
  - `Operator`, `Timestamp`, `Targets`, `RequestedFeatures`, `DryRun`, and a cryptographic SHA256 hash

## Tests

Pester tests:
- Dry-run ensures no install commands are invoked
- Idempotency confirms already-present features are skipped
- CSV validation catches malformed rows and halts before changes
- Logging test checks for a JSON artifact file creation (mocked)

Run:
```powershell
Invoke-Pester -Script .\tests\AdminSetup.Tests.ps1
```
