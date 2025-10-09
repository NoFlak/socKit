param(
  [Parameter(Mandatory=$true)]
  [string]$CsvPath
)
if (-not (Test-Path $CsvPath)) {
  Write-Error "CSV not found: $CsvPath"
  exit 2
}
# Expect header: Target,Features,Profile
$rows = Import-Csv -Path $CsvPath -Header Target,Features,Profile -UseCulture
$errs = @()
$i = 0
foreach ($r in $rows) {
  $i++
  if (-not $r.Target -or -not $r.Features) {
    $errs += "Line $i: Missing Target or Features"
    continue
  }
  # Features must be semicolon-separated (module splits ';')
  if ($r.Features -notmatch ";") {
    $errs += "Line $i: Features should be semicolon-separated: $($r.Features)"
  }
  if ($r.Profile -and ($r.Profile -match "\s")) {
    $errs += "Line $i: Profile must be a single token (no spaces): $($r.Profile)"
  }
}
if ($errs.Count -gt 0) {
  Write-Error "CSV validation failed:`n$($errs -join "`n")"
  exit 3
} else {
  Write-Output "CSV validation passed. Rows: $($rows.Count)"
  exit 0
}

