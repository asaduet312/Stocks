# Refresh PATH so Python is found in terminals opened before install.
$env:Path = [System.Environment]::GetEnvironmentVariable("Path", "Machine") + ";" +
            [System.Environment]::GetEnvironmentVariable("Path", "User")

$python = "C:\Users\skt31\AppData\Local\Programs\Python\Python312\python.exe"
if (-not (Test-Path $python)) {
    Write-Error "Python 3.12 not found. Install: winget install Python.Python.3.12"
    exit 1
}

Set-Location $PSScriptRoot
& $python examples/stock_analysis.py @args
