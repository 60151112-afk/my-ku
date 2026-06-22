param(
    [int]$Port = 8505,
    [string]$Python = "python"
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

if (-not $env:PUBLIC_DASHBOARD_ADMIN_PASSWORD -and -not $env:PUBLIC_DASHBOARD_ADMIN_PASSWORD_SHA256) {
    throw "Set PUBLIC_DASHBOARD_ADMIN_PASSWORD or PUBLIC_DASHBOARD_ADMIN_PASSWORD_SHA256 before starting admin."
}

& $Python -m streamlit run admin_site\app.py --server.port $Port --server.headless true
