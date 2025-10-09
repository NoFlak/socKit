#requires -Version 5.1
<#
.SYNOPSIS
  CLI wrapper for AdminSetup module with safe defaults and preview-first behavior.

.DESCRIPTION
  Demonstrates non-destructive usage. By default, runs in DryRun mode unless --force and explicit operator confirmation for risky profiles.

.PARAMETER profile
  Named profile mapping to feature sets: server-core, rdp-lan, desktop-standard, rdp-internet.

.PARAMETER features
  Comma-separated feature names to install (overrides profile features if provided).

.PARAMETER targets
  Single host or CSV path (Target,Features,Profile). CSV enables interactive per-target confirmation when --interactive is set.

.PARAMETER dry-run
  Runs without making changes (default). Omit to allow changes.

.PARAMETER force
  Required (with --confirm-operator) for public/internet profiles or public-facing features.

.PARAMETER confirm-operator
  Operator initials/name for gating.

.PARAMETER interactive
  Enable interactive prompts (CSV validation and confirmation).

.EXAMPLE
  .\scripts\install-admin-setup.ps1 --profile server-core --dry-run

.EXAMPLE
  .\scripts\install-admin-setup.ps1 --features Web-Server,DNS --confirm-operator BB --force

.EXAMPLE
  .\scripts\install-admin-setup.ps1 --targets .\targets.csv --interactive --confirm-operator BB
#>
[CmdletBinding()]
param(
  [Parameter()] [ValidateSet('server-core','rdp-lan','desktop-standard','rdp-internet')] [string] $profile,
  [Parameter()] [string] $features,
  [Parameter()] [string] $targets,
  [Parameter()] [switch] $dry_run = $true,
  [Parameter()] [switch] $force,
  [Parameter()] [string] $confirm_operator,
  [Parameter()] [switch] $interactive
)

$modulePath = Join-Path $PSScriptRoot '..\AdminSetup\AdminSetup.psm1' | Resolve-Path
Import-Module $modulePath -Force

# Map profiles to features
$profileMap = @{
  'server-core'      = @('AD-Domain-Services','DNS','DHCP')
  'rdp-lan'          = @('RDS-RD-Server')
  'desktop-standard' = @('NetFx3','TelnetClient')
  'rdp-internet'     = @('RDS-RD-Server','Web-Server')
}

$resolved = @()
if ($features) {
  $resolved = $features.Split(',') | ForEach-Object { $_.Trim() } | Where-Object { $_ }
} elseif ($profile) {
  $resolved = $profileMap[$profile]
}

if (($profile -match 'internet' -or $profile -match 'public') -and ([string]::IsNullOrWhiteSpace($confirm_operator) -or -not $force)) {
  Write-Error "Public/internet profile requires --force AND --confirm-operator"
  exit 1
}

$psParams = @{
  Feature          = $resolved
  DryRun           = $dry_run
  Force            = $force
  ConfirmOperator  = $confirm_operator
}

if ($interactive) { $psParams['Interactive'] = $true }

if ($targets) {
  if (Test-Path $targets) {
    # CSV-driven
    $psParams['Interactive'] = $true
    $psParams['CsvPath'] = $targets
  } else {
    # Single host target (local only in this wrapper)
    if ($targets -ne $env:COMPUTERNAME) {
      Write-Warning "This wrapper does not perform remote installs. Use CSV preview or run locally on the target."
      $psParams['DryRun'] = $true
    }
  }
}

$summary = Install-Features @psParams -Profile $profile -Verbose:$false
$summary | Format-List

