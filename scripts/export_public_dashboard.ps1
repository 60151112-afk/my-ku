param(
    [string]$Output = "public_site\public_data\dashboard_public_latest.json",
    [string]$Python = "python"
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

& $Python -m quant_trader.public_dashboard_export --project-root $ProjectRoot --output $Output
