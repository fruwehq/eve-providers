function Download-File {
  param(
    [Parameter(Mandatory=$true)][string]$Url,
    [Parameter(Mandatory=$true)][string]$OutFile,
    [int]$Retries = 5,
    [int]$RetryDelaySeconds = 2,
    [string]$UserAgent = "Mozilla/5.0",
    [switch]$SkipIfExists
  )

  if (-not (Get-Command curl.exe -ErrorAction SilentlyContinue)) {
    throw "curl.exe not found. This script requires curl to be available."
  }

  if ($SkipIfExists -and (Test-Path $OutFile)) {
    Write-Host "File already downloaded: $OutFile"
    return
  }

  $outDir = Split-Path -Parent $OutFile
  if ($outDir -and -not (Test-Path $outDir)) {
    New-Item -ItemType Directory -Path $outDir -Force | Out-Null
  }

  Write-Host "Downloading $Url -> $OutFile"
  $oldEap = $ErrorActionPreference
  $ErrorActionPreference = 'Continue'
  & curl.exe -L --fail --retry $Retries --retry-delay $RetryDelaySeconds --silent --show-error -A $UserAgent -o "$OutFile" "$Url"
  $exit = $LASTEXITCODE
  $ErrorActionPreference = $oldEap

  if ($exit -ne 0) {
    throw "curl download failed ($exit): $Url"
  }

  # Validate the download isn't an HTML redirect page disguised as a binary.
  # NoMachine's CDN returns 301→302→200 to their homepage HTML when the
  # version isn't available; curl saves the HTML silently.
  if (Test-Path $OutFile) {
    $bytes = [System.IO.File]::ReadAllBytes($OutFile)
    if ($bytes.Length -ge 2 -and $bytes[0] -eq 0x4D -and $bytes[1] -eq 0x5A) {
      # "MZ" magic — valid PE executable.
      return
    }
    # Not a PE: check if it looks like HTML (redirect page).
    $content = [System.Text.Encoding]::ASCII.GetString($bytes, 0, [Math]::Min(200, $bytes.Length))
    if ($content -match '<html|<!DOCTYPE|<head') {
      Remove-Item $OutFile -Force -ErrorAction SilentlyContinue
      throw "Downloaded file is an HTML page, not a binary. The URL may be stale or the version unavailable: $Url"
    }
  }
}
