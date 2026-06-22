param(
    [string]$SiteRoot = "public_site"
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

$SitePath = Join-Path $ProjectRoot $SiteRoot
$RequiredFiles = @(
    "index.html",
    ".nojekyll",
    "public_data\dashboard_public_latest.json",
    "public_data\dashboard_public_summary.csv"
)

foreach ($RelativePath in $RequiredFiles) {
    $Path = Join-Path $SitePath $RelativePath
    if (-not (Test-Path -LiteralPath $Path)) {
        throw "Missing required public site file: $RelativePath"
    }
}

$SensitivePatterns = @(
    "C:\\Users",
    "AppData",
    "Documents\\New project",
    "python.exe",
    "china_realtime_fresh_guard.py",
    "BEGIN PRIVATE KEY",
    "api_key",
    "secret_key",
    "password="
)

$Files = Get-ChildItem -LiteralPath $SitePath -Recurse -File
$Hits = @()
foreach ($File in $Files) {
    $Content = Get-Content -LiteralPath $File.FullName -Raw -Encoding UTF8 -ErrorAction SilentlyContinue
    foreach ($Pattern in $SensitivePatterns) {
        if ($Content -like "*$Pattern*") {
            $Hits += [PSCustomObject]@{
                File = $File.FullName
                Pattern = $Pattern
            }
        }
    }
}

if ($Hits.Count -gt 0) {
    $Hits | Format-Table -AutoSize | Out-String | Write-Output
    throw "Public site validation failed: sensitive markers found."
}

$JsonPath = Join-Path $SitePath "public_data\dashboard_public_latest.json"
$Json = Get-Content -LiteralPath $JsonPath -Raw -Encoding UTF8 | ConvertFrom-Json
if ($Json.site_type -ne "public_read_only_dashboard") {
    throw "Unexpected public dashboard site_type: $($Json.site_type)"
}
if ($Json.public_notice.broker_contacted -ne $false -or $Json.public_notice.order_submission_attempted -ne $false) {
    throw "Public notice boundary flags are not safe."
}

Write-Output "public_site_validation=ok"
Write-Output "site_root=$SitePath"
Write-Output "generated_at=$($Json.generated_at)"
