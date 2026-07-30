@echo off
setlocal
set "PYTHON=C:\Users\skt31\AppData\Local\Programs\Python\Python312\python.exe"
if not exist "%PYTHON%" (
    echo Python 3.12 not found at:
    echo   %PYTHON%
    echo Install from https://www.python.org/downloads/ or run: winget install Python.Python.3.12
    exit /b 1
)
cd /d "%~dp0"
"%PYTHON%" examples\stock_analysis.py %*
