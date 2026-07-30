# PSX Stock Analysis — launch web UI in browser
$env:Path = [System.Environment]::GetEnvironmentVariable("Path", "Machine") + ";" +
            [System.Environment]::GetEnvironmentVariable("Path", "User")

$python = "C:\Users\skt31\AppData\Local\Programs\Python\Python312\python.exe"
if (-not (Test-Path $python)) {
    Write-Host "Python 3.12 not found. Install: winget install Python.Python.3.12" -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}

Set-Location $PSScriptRoot
Write-Host ""
Write-Host " PSX Stock Analysis - starting web interface..." -ForegroundColor Cyan
Write-Host " Browser will open at http://localhost:8501" -ForegroundColor Green
Write-Host " Press Ctrl+C here to stop the app." -ForegroundColor Yellow
Write-Host ""

& $python -m pip install streamlit plotly -q
Start-Process "http://localhost:8501"
& $python -m streamlit run examples/stock_analysis_ui.py --server.headless true --server.port 8501 --browser.gatherUsageStats false
