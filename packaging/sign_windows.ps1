# Sign the built Texta.exe with a code-signing certificate.
#
# Required env vars (set as GitHub secrets in CI):
#   WIN_CODESIGN_CERT_PATH      Path to .pfx file (typically extracted from
#                               WIN_CODESIGN_CERT_BASE64 secret in CI)
#   WIN_CODESIGN_PASSWORD       Password for the .pfx
#
# When run without WIN_CODESIGN_CERT_PATH, prints a notice and exits 0
# (allows local builds without a cert).
param(
    [string]$Cert         = $env:WIN_CODESIGN_CERT_PATH,
    [string]$Password     = $env:WIN_CODESIGN_PASSWORD,
    [string]$TimestampUrl = "http://timestamp.digicert.com",
    [string]$Target       = "dist\Texta\Texta.exe"
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path $Target)) {
    throw "Built executable not found: $Target. Run pyinstaller first."
}

if (-not $Cert) {
    Write-Host "WIN_CODESIGN_CERT_PATH not set — skipping signing."
    Write-Host "(End users will see a SmartScreen warning until reputation is built.)"
    exit 0
}

# Locate signtool. On GitHub-hosted Windows runners, it's in the Windows SDK.
$signtool = Get-Command signtool -ErrorAction SilentlyContinue
if (-not $signtool) {
    $candidates = @(
        "${env:ProgramFiles(x86)}\Windows Kits\10\bin\10.0.22621.0\x64\signtool.exe",
        "${env:ProgramFiles(x86)}\Windows Kits\10\bin\10.0.22000.0\x64\signtool.exe",
        "${env:ProgramFiles(x86)}\Windows Kits\10\bin\10.0.20348.0\x64\signtool.exe",
        "${env:ProgramFiles(x86)}\Windows Kits\10\bin\10.0.19041.0\x64\signtool.exe"
    )
    $signtool = $candidates | Where-Object { Test-Path $_ } | Select-Object -First 1
    if (-not $signtool) {
        throw "signtool.exe not found. Install Windows SDK or add it to PATH."
    }
}

Write-Host "==> Signing $Target with $(Split-Path $Cert -Leaf)"
& $signtool sign `
    /f $Cert /p $Password `
    /tr $TimestampUrl /td sha256 /fd sha256 `
    $Target

Write-Host "==> Verifying signature"
& $signtool verify /pa /v $Target

Write-Host "==> Done."
