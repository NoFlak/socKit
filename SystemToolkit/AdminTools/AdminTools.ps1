#requires -Version 5.1
<#
.SYNOPSIS
  System Toolkit submenu for Admin Tools.

.DESCRIPTION
  Presents a minimal menu to run AdminSetup interactively, preview CSV runs, or show available features.
  - Defaults to DryRun for safety; requires explicit confirmation for real changes.
  - Writes run metadata to a local runs/ folder for audit.

#>

$ErrorActionPreference = 'Stop'
$modulePath = Join-Path $PSScriptRoot '..\..\AdminSetup\AdminSetup.psm1' | Resolve-Path
Import-Module $modulePath -Force

$runDir = Join-Path $PSScriptRoot 'runs'
if (-not (Test-Path $runDir)) { New-Item -ItemType Directory -Path $runDir | Out-Null }

function Save-RunMeta {
  param(
    [Parameter(Mandatory)][object] $Data
  )
  $ts = (Get-Date -Format o).Replace(':','-')
  $path = Join-Path $runDir "run-$ts.json"
  $Data | ConvertTo-Json -Depth 6 | Set-Content -Path $path -Encoding UTF8
  Write-Host "Saved run metadata to $path"
}

while ($true) {
  Clear-Host
  Write-Host "=== Admin Tools ==="
  Write-Host "1) Run AdminSetup (interactive)"
  Write-Host "2) Dry-run preview from CSV"
  Write-Host "3) Show available features"
  Write-Host "4) Upgrade apps with winget (preview by default)"
  Write-Host "5) Exit"
  $choice = Read-Host "Select option"

  switch ($choice) {
    '1' {
      $profile = Read-Host "Profile (server-core, rdp-lan, desktop-standard, rdp-internet or blank)"
      $confirm = if ($profile -match 'internet' -or $profile -match 'public') { Read-Host "Enter ConfirmOperator (required for public/internet)" } else { "" }
      try {
        $summary = Install-Features -Interactive -Profile $profile -ConfirmOperator $confirm -DryRun -Verbose:$false
        $summary | Format-List
        if ($summary.DryRun -eq $true) {
          $go = Read-Host "Proceed with real installation? Type YES to continue"
          if ($go -eq 'YES') {
            $summary = Install-Features -Interactive -Profile $profile -ConfirmOperator $confirm -Force -Verbose:$false
            $summary | Format-List
          } else {
            Write-Host "Aborted by operator."
          }
        }
        Save-RunMeta -Data ([pscustomobject]@{ Timestamp=(Get-Date).ToString('o'); Operator=$env:USERNAME; Mode='Interactive'; Profile=$profile; Summary=$summary })
      } catch {
        Write-Warning $_.Exception.Message
      }
      Pause
    }
    '2' {
      $csv = Read-Host "Enter CSV path (Target,Features,Profile)"
      if (-not (Test-Path $csv)) { Write-Warning "CSV not found."; Pause; break }
      try {
        $preview = Install-Features -Interactive -CsvPath $csv -DryRun -Verbose:$false
        $preview | Format-List
        Save-RunMeta -Data ([pscustomobject]@{ Timestamp=(Get-Date).ToString('o'); Operator=$env:USERNAME; Mode='CSV-Preview'; CSV=$csv; Preview=$preview })
      } catch {
        Write-Warning $_.Exception.Message
      }
      Pause
    }
    '3' {
      Get-AvailableTargetFeatures | Sort-Object Target,Name | Format-Table Target,Name,DisplayName,Notes -AutoSize
      Pause
    }
    '4' {
      try {
        $preview = Update-WinGetPackages -DryRun
        $preview | Format-List
        $go = Read-Host "Proceed with winget upgrade? Type YES to continue"
        if ($go -eq 'YES') {
          $result = Update-WinGetPackages -Force
          $result | Format-List
        } else {
          Write-Host "Winget upgrade aborted by operator."
        }
        Save-RunMeta -Data ([pscustomobject]@{ Timestamp=(Get-Date).ToString('o'); Operator=$env:USERNAME; Mode='winget'; Preview=$preview })
      } catch {
        Write-Warning $_.Exception.Message
      }
      Pause
    }
    '5' { break }
    default { Write-Host "Invalid selection."; Pause }
  }
}
