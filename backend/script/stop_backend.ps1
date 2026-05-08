param(
    [int]$Port = 8000
)

$connections = Get-NetTCPConnection -LocalPort $Port -ErrorAction SilentlyContinue
$processIds = $connections | Select-Object -ExpandProperty OwningProcess -Unique

if (-not $processIds) {
    Write-Host "No backend process found on port $Port."
    exit 0
}

foreach ($processId in $processIds) {
    $process = Get-Process -Id $processId -ErrorAction SilentlyContinue
    if (-not $process) {
        continue
    }

    Write-Host "Stopping process $($process.ProcessName) ($processId) on port $Port..."
    Stop-Process -Id $processId -Force
}

Write-Host "Backend processes on port $Port stopped."
