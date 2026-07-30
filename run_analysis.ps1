# Refresh PATH so Python is found in terminals opened before install.
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
    Write-Error "Python 3.11+ not found. Install: winget install Python.Python.3.12"
    exit 1
}

Set-Location $PSScriptRoot
& $python examples/stock_analysis.py @args
