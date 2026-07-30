@echo off
setlocal
cd /d "%~dp0"

set "PYTHON="
where python >nul 2>&1
if %errorlevel%==0 (
    for /f "delims=" %%i in ('where python') do (
        echo %%i | findstr /i "WindowsApps" >nul
        if errorlevel 1 (
            set "PYTHON=%%i"
            goto :found
        )
    )
)
if exist "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" set "PYTHON=%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
if not defined PYTHON if exist "%LOCALAPPDATA%\Programs\Python\Python311\python.exe" set "PYTHON=%LOCALAPPDATA%\Programs\Python\Python311\python.exe"
if not defined PYTHON if exist "%~dp0.venv\Scripts\python.exe" set "PYTHON=%~dp0.venv\Scripts\python.exe"

:found
if not defined PYTHON (
    echo Python 3.11+ not found at a known location.
    echo Install from https://www.python.org/downloads/ or run: winget install Python.Python.3.12
    exit /b 1
)

"%PYTHON%" examples\stock_analysis.py %*
