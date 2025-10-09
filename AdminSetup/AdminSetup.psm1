#requires -Version 5.1
<#
.SYNOPSIS
  AdminSetup PowerShell module: safe-by-default feature provisioning with previews, gating, logging, and CSV workflows.

.DESCRIPTION
  - Safety-first: prechecks, idempotency, dry-run default in production.
  - Supports Server (Install-WindowsFeature) and Client (DISM/Enable-WindowsOptionalFeature).
  - CSV-driven multi-target validation with explicit confirmation.
  - Logs transcript and JSON summary to C:\ProgramData\AdminSetup\artifacts\<ISO8601>\.
  - Includes SHA256 hash derived from invocation and operator.
  - No network/firewall changes are performed unless Force AND ConfirmOperator AND approved Profile.

.NOTES
  This module avoids remote executions: non-local targets are validated and previewed, and require a separate remoting tool for actual changes.

#>

Set-StrictMode -Version Latest

#region Helpers

function New-AdminSetupArtifactPath {
  [CmdletBinding()]
  param(
    [Parameter()] [ValidateNotNullOrEmpty()] [string] $Root = 'C:\ProgramData\AdminSetup\artifacts',
    [Parameter()] [ValidateNotNullOrEmpty()] [string] $Timestamp = (Get-Date -Format o).Replace(':','-')
  )
  $path = Join-Path $Root $Timestamp
  if (-not (Test-Path $path)) {
    New-Item -ItemType Directory -Path $path -Force | Out-Null
  }
  return $path
}

function Write-AdminSetupJson {
  [CmdletBinding()]
  param(
    [Parameter(Mandatory)][ValidateNotNull()] [object] $Object,
    [Parameter(Mandatory)][ValidateNotNullOrEmpty()] [string] $Path
  )
  $json = $Object | ConvertTo-Json -Depth 6
  Set-Content -Path $Path -Value $json -Encoding UTF8
  return $Path
}

function Get-AdminHash {
  [CmdletBinding()]
  param(
    [Parameter(Mandatory)][string] $InputText
  )
  $bytes = [System.Text.Encoding]::UTF8.GetBytes($InputText)
  $sha = [System.Security.Cryptography.SHA256]::Create()
  $hashBytes = $sha.ComputeHash($bytes)
  -join ($hashBytes | ForEach-Object { '{0:x2}' -f $_ })
}

function Test-IsAdmin {
  [CmdletBinding()]
  param()
  try {
    $id = [Security.Principal.WindowsIdentity]::GetCurrent()
    $p = New-Object Security.Principal.WindowsPrincipal($id)
    return $p.IsInRole([Security.Principal.WindowsBuiltinRole]::Administrator)
  } catch { return $false }
}

function Get-IsServerOS {
  [CmdletBinding()]
  param()
  try {
    $edition = (Get-ItemProperty 'HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion').EditionID
    return ($edition -match 'Server')
  } catch { return $false }
}

function Get-IsDomainJoined {
  [CmdletBinding()]
  param()
  try {
    $cs = Get-CimInstance -ClassName Win32_ComputerSystem -ErrorAction Stop
    return [bool]$cs.PartOfDomain
  } catch { return $false }
}

function Get-IsProduction {
  [CmdletBinding()]
  param(
    [Parameter()] [string] $FlagPath = 'C:\ProgramData\ProductionFlag'
  )
  return (Test-Path $FlagPath) -or (Get-IsDomainJoined)
}

function Confirm-PublicProfile {
  [CmdletBinding()]
  param(
    [Parameter(Mandatory)][string] $Profile,
    [Parameter(Mandatory)][string] $ConfirmOperator,
    [Parameter()] [switch] $Force
  )
  $needsGate = ($Profile -match 'internet' -or $Profile -match 'public')
  if ($needsGate -or $Force) {
    if ([string]::IsNullOrWhiteSpace($ConfirmOperator)) {
      throw "Public-facing profile or Force requested requires -ConfirmOperator with operator initials/name."
    }
  }
  return $true
}

#endregion Helpers

function Test-AdminPrereqs {
  [CmdletBinding()]
  param(
    [Parameter()] [string] $ProductionFlagPath = 'C:\ProgramData\ProductionFlag'
  )

  $reasons = New-Object System.Collections.Generic.List[string]
  $isAdmin = Test-IsAdmin
  $isWindows = $true
  $isDomain = Get-IsDomainJoined
  $isProd = (Test-Path $ProductionFlagPath) -or $isDomain

  if (-not $isAdmin) { $reasons.Add('Not running with administrative privileges.') }
  if (-not $isWindows) { $reasons.Add('Unsupported OS. Windows required.') }
  if ($isProd) { $reasons.Add('Production safeguards enabled (flag file or domain join detected).') }

  [pscustomobject]@{
    Success        = $isAdmin -and $isWindows
    Reasons        = $reasons.ToArray()
    IsAdmin        = $isAdmin
    IsWindows      = $isWindows
    IsDomainJoined = $isDomain
    Production     = $isProd
  }
}

function Get-AvailableTargetFeatures {
  [CmdletBinding()]
  param()

  $list = @(
    # Server roles
    [pscustomobject]@{ Name='DNS';            DisplayName='DNS Server';           Target='Server'; Notes='Core infra DNS role'; PublicFacing=$false }
    [pscustomobject]@{ Name='DHCP';           DisplayName='DHCP Server';          Target='Server'; Notes='Core infra DHCP role'; PublicFacing=$false }
    [pscustomobject]@{ Name='AD-Domain-Services'; DisplayName='Active Directory Domain Services'; Target='Server'; Notes='AD DS'; PublicFacing=$false }
    [pscustomobject]@{ Name='Web-Server';     DisplayName='IIS Web Server';       Target='Server'; Notes='Web server (public-facing risk)'; PublicFacing=$true }
    [pscustomobject]@{ Name='RDS-RD-Server';  DisplayName='Remote Desktop Services'; Target='Server'; Notes='RDP (internet-facing risk)'; PublicFacing=$true }

    # Client features
    [pscustomobject]@{ Name='NetFx3';         DisplayName='.NET Framework 3.5';   Target='Client'; Notes='Client optional feature'; PublicFacing=$false }
    [pscustomobject]@{ Name='TelnetClient';   DisplayName='Telnet Client';         Target='Client'; Notes='Legacy tool'; PublicFacing=$false }
    [pscustomobject]@{ Name='Microsoft-Hyper-V-All'; DisplayName='Hyper-V';        Target='Client'; Notes='Virtualization'; PublicFacing=$false }
    [pscustomobject]@{ Name='IIS-WebServerRole'; DisplayName='IIS (Client)';      Target='Client'; Notes='Web server (public-facing risk)'; PublicFacing=$true }
  )
  return $list
}

function Resolve-FeatureCommand {
  [CmdletBinding()]
  param(
    [Parameter(Mandatory)][ValidateNotNullOrEmpty()] [string] $Name,
    [Parameter()] [ValidateSet('Server','Client','Auto')] [string] $Target = 'Auto'
  )

  $isServer = if ($Target -eq 'Auto') { Get-IsServerOS } else { $Target -eq 'Server' }
  if ($isServer) {
    $detect = {
      param($FeatureName)
      $f = Get-WindowsFeature -Name $FeatureName -ErrorAction SilentlyContinue
      if ($null -eq $f) { return $false }
      return [bool]$f.Installed
    }
    $install = "Install-WindowsFeature -Name {0} -IncludeManagementTools -ErrorAction Stop"
    return [pscustomobject]@{
      Target = 'Server'
      Detect = $detect
      InstallTemplate = $install
    }
  } else {
    $detect = {
      param($FeatureName)
      $of = Get-WindowsOptionalFeature -Online -FeatureName $FeatureName -ErrorAction SilentlyContinue
      if ($null -eq $of) { return $false }
      return ($of.State -eq 'Enabled')
    }
    $install = "Enable-WindowsOptionalFeature -Online -FeatureName {0} -All -NoRestart -ErrorAction Stop"
    return [pscustomobject]@{
      Target = 'Client'
      Detect = $detect
      InstallTemplate = $install
    }
  }
}

function Install-WindowsServerFeatures {
  [CmdletBinding(SupportsShouldProcess=$true)]
  param(
    [Parameter(Mandatory)][string[]] $Feature,
    [Parameter()] [switch] $DryRun,
    [Parameter()] [switch] $Force
  )

  $actions = @()
  foreach ($f in $Feature) {
    $present = (Get-WindowsFeature -Name $f -ErrorAction SilentlyContinue)
    if ($present -and $present.Installed) {
      $actions += [pscustomobject]@{ Feature=$f; Action='AlreadyPresent'; Result='Skipped' }
      continue
    }
    $cmd = "Install-WindowsFeature -Name $f -IncludeManagementTools -ErrorAction Stop"
    if ($DryRun -or -not $PSCmdlet.ShouldProcess($env:COMPUTERNAME, "Install $f")) {
      $actions += [pscustomobject]@{ Feature=$f; Action='Install'; Result='Preview'; Command=$cmd }
      continue
    }
    try {
      Invoke-Expression $cmd | Out-Null
      $actions += [pscustomobject]@{ Feature=$f; Action='Install'; Result='Success'; Command=$cmd }
    } catch {
      $actions += [pscustomobject]@{ Feature=$f; Action='Install'; Result='Failed'; Error=$_.Exception.Message; Command=$cmd }
    }
  }
  return $actions
}

function Install-ClientFeatures {
  [CmdletBinding(SupportsShouldProcess=$true)]
  param(
    [Parameter(Mandatory)][string[]] $Feature,
    [Parameter()] [switch] $DryRun,
    [Parameter()] [switch] $Force
  )

  $actions = @()
  foreach ($f in $Feature) {
    $of = Get-WindowsOptionalFeature -Online -FeatureName $f -ErrorAction SilentlyContinue
    if ($of -and $of.State -eq 'Enabled') {
      $actions += [pscustomobject]@{ Feature=$f; Action='AlreadyPresent'; Result='Skipped' }
      continue
    }
    $cmd = "Enable-WindowsOptionalFeature -Online -FeatureName $f -All -NoRestart -ErrorAction Stop"
    if ($DryRun -or -not $PSCmdlet.ShouldProcess($env:COMPUTERNAME, "Enable $f")) {
      $actions += [pscustomobject]@{ Feature=$f; Action='Install'; Result='Preview'; Command=$cmd }
      continue
    }
    try {
      Invoke-Expression $cmd | Out-Null
      $actions += [pscustomobject]@{ Feature=$f; Action='Install'; Result='Success'; Command=$cmd }
    } catch {
      $actions += [pscustomobject]@{ Feature=$f; Action='Install'; Result='Failed'; Error=$_.Exception.Message; Command=$cmd }
    }
  }
  return $actions
}

function Get-InstallSummary {
  [CmdletBinding()]
  param(
    [Parameter(Mandatory)][datetime] $Timestamp,
    [Parameter(Mandatory)][string] $Operator,
    [Parameter(Mandatory)][string[]] $Targets,
    [Parameter(Mandatory)][string[]] $RequestedFeatures,
    [Parameter(Mandatory)][object[]] $Actions,
    [Parameter()][switch] $DryRun,
    [Parameter()][string] $Profile,
    [Parameter()][string] $LogPath,
    [Parameter()][string] $Hash
  )

  [pscustomobject]@{
    Timestamp         = $Timestamp.ToString("o")
    Operator          = $Operator
    Targets           = $Targets
    RequestedFeatures = $RequestedFeatures
    Actions           = $Actions
    DryRun            = [bool]$DryRun
    Profile           = $Profile
    LogPath           = $LogPath
    Hash              = $Hash
  }
}

function Install-Features {
  [CmdletBinding(SupportsShouldProcess=$true)]
  param(
    [Parameter()] [string[]] $Feature,
    [Parameter()] [switch] $DryRun,
    [Parameter()] [switch] $Force,
    [Parameter()] [string] $ConfirmOperator,
    [Parameter()] [string[]] $Whitelist,
    [Parameter()] [string] $Profile,
    [Parameter()] [string] $LogPath,
    [Parameter()] [switch] $Interactive,
    [Parameter()] [string] $CsvPath
  )

  begin {
    Write-Verbose "Starting Install-Features"
    $ts = Get-Date
    $operator = $env:USERNAME
    $targets = @($env:COMPUTERNAME)
    $prod = Get-IsProduction
    # Default to DryRun in production unless operator explicitly disables it
    if ($prod -and -not $PSBoundParameters.ContainsKey('DryRun')) {
      $DryRun = $true
    }
    # Safety gating for public/internet profiles
    if ($Profile) {
      Confirm-PublicProfile -Profile $Profile -ConfirmOperator $ConfirmOperator -Force:$Force | Out-Null
    }
    $artifactsRoot = if ($LogPath) { $LogPath } else { 'C:\ProgramData\AdminSetup\artifacts' }
    $artifactDir = New-AdminSetupArtifactPath -Root $artifactsRoot
    $transcript = Join-Path $artifactDir 'transcript.txt'
    $summaryPath = Join-Path $artifactDir 'summary.json'
    $shaPath = Join-Path $artifactDir 'summary.sha256'
    $requested = @()
    $allActions = @()
    $publicRisks = (Get-AvailableTargetFeatures | Where-Object { $_.PublicFacing }) | ForEach-Object { $_.Name }

    # Interactive CSV: Target,Features,Profile
    if ($Interactive) {
      $pathToCsv = if ($CsvPath) { $CsvPath } else { Read-Host "Enter CSV path (columns: Target, Features (semicolon-separated), Profile)" }
      if (-not (Test-Path $pathToCsv)) {
        throw "CSV path not found: $pathToCsv"
      }
      $rows = Import-Csv -Path $pathToCsv
      $errors = @()
      $parsed = @()
      foreach ($row in $rows) {
        $t = ($row.Target | ForEach-Object { ($_ -as [string]).Trim() })
        $fs = ($row.Features | ForEach-Object { ($_ -as [string]).Split(';') | ForEach-Object { $_.Trim() } | Where-Object { $_ } })
        $pf = ($row.Profile | ForEach-Object { ($_ -as [string]).Trim() })
        if (-not $t) { $errors += "Row missing Target" }
        if (-not $fs -or $fs.Count -eq 0) { $errors += "Row missing Features for target $t" }
        if ($pf -and ($pf -match 'internet' -or $pf -match 'public') -and [string]::IsNullOrWhiteSpace($ConfirmOperator)) {
          $errors += "Public-facing profile for $t requires -ConfirmOperator"
        }
        $parsed += [pscustomobject]@{ Target=$t; Features=$fs; Profile=$pf }
      }
      if ($errors.Count -gt 0) {
        $errText = ($errors -join "; ")
        Set-Content -Path $transcript -Value "CSV validation errors: $errText" -Encoding UTF8
        $hash = Get-AdminHash -InputText "$operator|$($ts.ToString('o'))|$errText"
        $sum = Get-InstallSummary -Timestamp $ts -Operator $operator -Targets ($parsed.Target) -RequestedFeatures @() -Actions @() -DryRun:$true -Profile $Profile -LogPath $artifactDir -Hash $hash
        Write-AdminSetupJson -Object $sum -Path $summaryPath | Out-Null
        Set-Content -Path $shaPath -Value $hash -Encoding ASCII
        return [pscustomobject]@{ Validation='Failed'; Errors=$errors }
      }
      # Confirm grouped preview
      $targets = $parsed.Target
      $Feature = @() # override requested feature list to union from CSV
      foreach ($row in $parsed) { $Feature += $row.Features }
      $Feature = $Feature | Select-Object -Unique
      $previewLines = $parsed | ForEach-Object { "$($_.Target): $($_.Features -join ', ') [Profile=$($_.Profile)]" }
      $previewText = "Preview (DryRun=$($DryRun.IsPresent))`n" + ($previewLines -join "`n")
      Write-Host $previewText
      if (-not $DryRun) {
        $ok = Read-Host "Proceed with real installation? Type YES to continue"
        if ($ok -ne 'YES') { return [pscustomobject]@{ Confirmation='AbortedByOperator'; Preview=$previewLines } }
    }

    # Whitelist enforcement (local scope)
    if ($Whitelist -and $Whitelist.Count -gt 0) {
      if ($targets | Where-Object { $_ -notin $Whitelist }) {
        throw "Current host '$($env:COMPUTERNAME)' is not in whitelist. Add to -Whitelist to proceed."
      }
    }

    # Public-facing feature safety gate
    if (($Feature | Where-Object { $_ -in $publicRisks }).Count -gt 0) {
      if ([string]::IsNullOrWhiteSpace($ConfirmOperator) -or -not $Force) {
        throw "Public-facing feature selection requires both -Force and -ConfirmOperator."
      }
    }

    # Capture invocation hash
    $invocation = "$operator|$($ts.ToString('o'))|$($targets -join ',')|$($Feature -join ',')|$Profile|$($DryRun.IsPresent)"
    $hash = Get-AdminHash -InputText $invocation
    Set-Content -Path $transcript -Value "Operator=$operator`nTimestamp=$($ts.ToString('o'))`nTargets=$($targets -join ',')`nFeatures=$($Feature -join ',')`nProfile=$Profile`nDryRun=$($DryRun.IsPresent)`nHash=$hash" -Encoding UTF8

    # Expand requested
    $requested = if ($Feature) { $Feature } else { @() }
    $isServer = Get-IsServerOS
    $actions = if ($isServer) {
      Install-WindowsServerFeatures -Feature $requested -DryRun:$DryRun -Force:$Force
    } else {
      Install-ClientFeatures -Feature $requested -DryRun:$DryRun -Force:$Force
    }
    $allActions += $actions

    $summary = Get-InstallSummary -Timestamp $ts -Operator $operator -Targets $targets -RequestedFeatures $requested -Actions $allActions -DryRun:$DryRun -Profile $Profile -LogPath $artifactDir -Hash $hash
    Write-AdminSetupJson -Object $summary -Path $summaryPath | Out-Null
    Set-Content -Path $shaPath -Value $hash -Encoding ASCII
    return $summary
  }
}

Export-ModuleMember -Function `
  Test-AdminPrereqs, `
  Get-AvailableTargetFeatures, `
  Resolve-FeatureCommand, `
  Install-Features, `
  Install-WindowsServerFeatures, `
  Install-ClientFeatures, `
  Get-InstallSummary

# region WinGet Upgrades

function Update-WinGetPackages {
  [CmdletBinding()]
  param(
    [Parameter()] [switch] $DryRun,
    [Parameter()] [switch] $IncludeUnknown,
    [Parameter()] [switch] $Force,
    [Parameter()] [string] $LogPath
  )

  $ts = Get-Date
  $operator = $env:USERNAME
  $artifactsRoot = if ($LogPath) { $LogPath } else { 'C:\ProgramData\AdminSetup\artifacts' }
  $artifactDir = New-AdminSetupArtifactPath -Root $artifactsRoot
  $transcript = Join-Path $artifactDir 'winget-transcript.txt'
  $summaryPath = Join-Path $artifactDir 'winget-summary.json'

  # Prechecks
  $winget = Get-Command winget -ErrorAction SilentlyContinue
  if (-not $winget) { throw "winget CLI not found. Install from Microsoft Store or App Installer." }

  # List available upgrades (preview)
  $listArgs = @('upgrade')
  if ($IncludeUnknown) { $listArgs += '--include-unknown' }
  $list = & winget @listArgs 2>&1 | Out-String
  Set-Content -Path $transcript -Value $list -Encoding UTF8

  $actions = @()
  $available = ($list -split "`r?`n") | Where-Object { $_ -and ($_ -notmatch '^Name\s+Id\s+') -and ($_ -notmatch '^----') }
  foreach ($line in $available) { $actions += [pscustomobject]@{ Line=$line } }

  if ($DryRun) {
    $hash = Get-AdminHash -InputText "$operator|$($ts.ToString('o'))|winget|preview|$($IncludeUnknown.IsPresent)"
    $sum = [pscustomobject]@{
      Timestamp = $ts.ToString('o')
      Operator  = $operator
      Mode      = 'winget-preview'
      DryRun    = $true
      IncludeUnknown = [bool]$IncludeUnknown
      Actions   = $actions
      LogPath   = $artifactDir
      Hash      = $hash
    }
    Write-AdminSetupJson -Object $sum -Path $summaryPath | Out-Null
    return $sum
  }

  # Real upgrade requires Force acknowledgement
  if (-not $Force) { throw "Upgrading packages requires -Force acknowledgement." }

  $upgradeArgs = @('upgrade','--all','--accept-source-agreements','--accept-package-agreements','--silent')
  if ($IncludeUnknown) { $upgradeArgs += '--include-unknown' }
  $upgradeOut = & winget @upgradeArgs 2>&1 | Out-String
  Add-Content -Path $transcript -Value "`n==== UPGRADE OUTPUT ====`n$upgradeOut" -Encoding UTF8

  $hash2 = Get-AdminHash -InputText "$operator|$($ts.ToString('o'))|winget|upgrade|$($IncludeUnknown.IsPresent)"
  $sum2 = [pscustomobject]@{
    Timestamp = $ts.ToString('o')
    Operator  = $operator
    Mode      = 'winget-upgrade'
    DryRun    = $false
    IncludeUnknown = [bool]$IncludeUnknown
    Actions   = $actions
    LogPath   = $artifactDir
    Hash      = $hash2
  }
  Write-AdminSetupJson -Object $sum2 -Path $summaryPath | Out-Null
  return $sum2
}

Export-ModuleMember -Function Update-WinGetPackages

# endregion WinGet Upgrades
