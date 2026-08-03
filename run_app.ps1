# PSX Stock Analysis — launch web UI in browser (cross-user, PATH-aware)
$ErrorActionPreference = "Stop"

$env:Path = [System.Environment]::GetEnvironmentVariable("Path", "Machine") + ";" +
            [System.Environment]::GetEnvironmentVariable("Path", "User")

function Find-Python {
    $cmd = Get-Command python -ErrorAction SilentlyContinue
    if ($cmd -and $cmd.Source -notmatch "WindowsApps") {
        return $cmd.Source
    }
    $candidates = @(
        "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe",
        "$env:LOCALAPPDATA\Programs\Python\Python311\python.exe",
        "$PSScriptRoot\.venv\Scripts\python.exe"
    )
    foreach ($p in $candidates) {
        if (Test-Path $p) { return $p }
    }
    return $null
}

$python = Find-Python
if (-not $python) {
    Write-Host "Python 3.11+ not found. Install: winget install Python.Python.3.12" -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}

Set-Location $PSScriptRoot
Write-Host ""
Write-Host " Stocks Dashboard - starting web interface..." -ForegroundColor Cyan
Write-Host " Browser will open at http://localhost:8501" -ForegroundColor Green
Write-Host " Press Ctrl+C here to stop the app." -ForegroundColor Yellow
Write-Host ""

& $python -m pip install -r requirements.txt -q
Start-Process "http://localhost:8501"
& $python -m streamlit run examples/stock_analysis_ui.py --server.headless true --server.port 8501 --server.address 0.0.0.0 --browser.gatherUsageStats false
