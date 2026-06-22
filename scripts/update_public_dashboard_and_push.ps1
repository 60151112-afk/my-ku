param(
    [string]$Python = "python",
    [string]$Message = "Update public dashboard snapshot",
    [switch]$NoPush,
    [switch]$ValidateOnly,
    [switch]$SkipExport,
    [switch]$SkipTests
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

$PreStaged = & git diff --cached --name-only
if ($PreStaged) {
    throw "Refusing to continue: staged files already exist. Commit or unstage them first."
}

if (-not $SkipExport) {
    & $Python -m quant_trader.public_dashboard_export --project-root $ProjectRoot --output "public_site\public_data\dashboard_public_latest.json"
}

& powershell -ExecutionPolicy Bypass -File "scripts\validate_public_dashboard_static_site.ps1"

if (-not $SkipTests) {
    & $Python -m unittest tests.test_public_dashboard_export
}

if ($ValidateOnly) {
    Write-Output "validate_only=ok"
    exit 0
}

$PublicPaths = @(
    ".github\workflows\deploy-public-dashboard.yml",
    "Dockerfile.public-dashboard",
    "public_site\.nojekyll",
    "public_site\.streamlit\config.toml",
    "public_site\README.md",
    "public_site\app.py",
    "public_site\index.html",
    "public_site\requirements.txt",
    "public_site\public_data\dashboard_public_latest.json",
    "public_site\public_data\dashboard_public_summary.csv",
    "quant_trader\public_dashboard_export.py",
    "scripts\build_public_dashboard_static_package.ps1",
    "scripts\export_public_dashboard.ps1",
    "scripts\update_public_dashboard_and_push.ps1",
    "scripts\validate_public_dashboard_static_site.ps1",
    "tests\test_public_dashboard_export.py"
)

& git add -- $PublicPaths
& git diff --cached --check

$Staged = & git diff --cached --name-only
if (-not $Staged) {
    Write-Output "no_public_changes_to_commit=1"
    exit 0
}

Write-Output "staged_public_files:"
$Staged | ForEach-Object { Write-Output "  $_" }

& git commit -m $Message

if (-not $NoPush) {
    & git push origin HEAD:main
}

Write-Output "public_dashboard_update=ok"
