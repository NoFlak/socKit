# Auto-generated AutoMenu.ps1 - SAMPLE
# Generated from menus/menu.yml (static sample committed for reference)
# PLACEHOLDER: Keep this sentinel so generators preserve manual edits.
# To regenerate, run: python tools/generate_menus.py --force

$ErrorActionPreference = 'Stop'

function Show-AutoMenu {
  Clear-Host
  Write-Host '=== Auto Admin Tools ==='
  Write-Host "\n## System Tools ##"
  Write-Host '[1] System Overview'
  Write-Host '[2] Enumerate Services (preview)'
  Write-Host '[3] Critical Path Inventory'
  Write-Host '[4] System File Checker'
  Write-Host "\n## Network Tools ##"
  Write-Host '[5] Ping Test'
  Write-Host '[6] DNS Health'
  Write-Host '[7] TCP Port Scan'
  Write-Host "\n## Admin Tools ##"
  Write-Host '[8] AdminSetup Submenu (PowerShell)'
  Write-Host '[9] WinGet Upgrade (preview)'
  Write-Host "\n## Detailed System Toolkit ##"
  Write-Host '[10] Repair All'
  Write-Host '[11] Package Repair'
  Write-Host '[12] Disk Cleanup'
  Write-Host '[13] Network Reset'
  Write-Host '[14] Resource Monitor'
  Write-Host '[15] GPU Monitor'
  Write-Host '[16] Thermal Check'
  Write-Host '[17] Startup Auditor'
  Write-Host '[18] Scheduled Tasks'
  Write-Host '[19] Power Settings'
  Write-Host "\n[q] Quit"
}

function Invoke-AutoMenu {
  param([string]$choice)
  switch ($choice) {
    '1'  { Write-Host 'Would run task: system.overview' ; break }
    '2'  { Write-Host 'Would run task: system.services' ; break }
    '3'  { Write-Host 'Would run task: system.paths' ; break }
    '4'  { Write-Host 'Would run task: system.sfc' ; break }
    '5'  { Write-Host 'Would run task: network.ping' ; break }
    '6'  { Write-Host 'Would run task: network.dns_health' ; break }
    '7'  { Write-Host 'Would run task: network.tcp_scan' ; break }
    '8'  { Write-Host 'Would launch: SystemToolkit/AdminTools/AdminTools.ps1' ; break }
    '9'  { Write-Host 'Would run task: admin.winget_upgrade (dry-run)' ; break }
    '10' { Write-Host 'Would run task: system.repair_all' ; break }
    '11' { Write-Host 'Would run task: system.package_repair' ; break }
    '12' { Write-Host 'Would run task: system.disk_cleanup' ; break }
    '13' { Write-Host 'Would run task: system.network_reset' ; break }
    '14' { Write-Host 'Would run task: system.resource_monitor' ; break }
    '15' { Write-Host 'Would run task: system.gpu_monitor' ; break }
    '16' { Write-Host 'Would run task: system.thermal_check' ; break }
    '17' { Write-Host 'Would run task: system.startup_auditor' ; break }
    '18' { Write-Host 'Would run task: system.scheduled_tasks' ; break }
    '19' { Write-Host 'Would run task: system.power_settings' ; break }
    default { Write-Host 'Unknown selection' }
  }
}

while ($true) {
  Show-AutoMenu
  $sel = Read-Host 'Select'
  if ($sel -eq 'q') { break }
  Invoke-AutoMenu -choice $sel
  Read-Host 'Press Enter to continue'
}
