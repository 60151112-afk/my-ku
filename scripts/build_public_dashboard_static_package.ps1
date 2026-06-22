param(
    [string]$OutputRoot = "outputs\public_dashboard_static",
    [string]$Python = "python"
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

& $Python -m quant_trader.public_dashboard_export --project-root $ProjectRoot --output "public_site\public_data\dashboard_public_latest.json"

$Stamp = Get-Date -Format "yyyyMMddTHHmmss"
$OutputRootPath = Join-Path $ProjectRoot $OutputRoot
$StageRoot = Join-Path $OutputRootPath "stage"
$Stage = Join-Path $StageRoot "public_dashboard_static_$Stamp"
$ZipPath = Join-Path $OutputRootPath "public_dashboard_static_$Stamp.zip"

New-Item -ItemType Directory -Force -Path $Stage | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $Stage "public_data") | Out-Null

Copy-Item -LiteralPath (Join-Path $ProjectRoot "public_site\index.html") -Destination (Join-Path $Stage "index.html") -Force
Copy-Item -LiteralPath (Join-Path $ProjectRoot "public_site\.nojekyll") -Destination (Join-Path $Stage ".nojekyll") -Force
Copy-Item -LiteralPath (Join-Path $ProjectRoot "public_site\public_data\dashboard_public_latest.json") -Destination (Join-Path $Stage "public_data\dashboard_public_latest.json") -Force
Copy-Item -LiteralPath (Join-Path $ProjectRoot "public_site\public_data\dashboard_public_summary.csv") -Destination (Join-Path $Stage "public_data\dashboard_public_summary.csv") -Force

if (Test-Path -LiteralPath $ZipPath) {
    Remove-Item -LiteralPath $ZipPath -Force
}
Compress-Archive -Path (Join-Path $Stage "*") -DestinationPath $ZipPath -Force

Write-Output "static_package=$ZipPath"
Write-Output "stage_dir=$Stage"
