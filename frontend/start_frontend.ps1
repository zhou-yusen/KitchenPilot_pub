param(
    [int]$Port = 5173,
    [string]$HostAddress = "127.0.0.1"
)

$ErrorActionPreference = "Stop"
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptDir

$python = Get-Command python -ErrorAction SilentlyContinue
if (-not $python) {
    $backendPython = Join-Path $scriptDir "..\backend\.venv\Scripts\python.exe"
    if (Test-Path $backendPython) {
        $python = Get-Item $backendPython
    }
}

if (-not $python) {
    Write-Error "Python not found. Install Python or run backend uv sync first."
    exit 1
}

$url = "http://${HostAddress}:$Port"
Write-Host "KitchenPilot frontend running:"
Write-Host "  $url"
Write-Host ""
Write-Host "Press Ctrl+C to stop."
Write-Host ""

& $python.Source -m http.server $Port --bind $HostAddress
