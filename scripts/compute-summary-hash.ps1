param(
  [Parameter(Mandatory=$true)][string]$Operator,
  [Parameter(Mandatory=$true)][string[]]$Targets,
  [Parameter(Mandatory=$true)][string[]]$RequestedFeatures,
  [Parameter(Mandatory=$true)][string]$Profile
)
# Canonical, ordered object for deterministic hash
$summary = [ordered]@{
  Operator = $Operator
  Timestamp = (Get-Date).ToUniversalTime().ToString("o")
  Profile = $Profile
  Targets = $Targets
  RequestedFeatures = $RequestedFeatures
}
$json = $summary | ConvertTo-Json -Depth 5 -Compress
$bytes = [System.Text.Encoding]::UTF8.GetBytes($json)
$sha   = [System.BitConverter]::ToString( (New-Object System.Security.Cryptography.SHA256Managed).ComputeHash($bytes) ) -replace "-",""
$sha   = $sha.ToLowerInvariant()
Write-Output $json
Write-Output "`nSHA256: $sha"

