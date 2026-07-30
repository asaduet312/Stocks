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
    echo Python 3.11+ not found. Install: winget install Python.Python.3.12
    pause
    exit /b 1
)

echo.
echo  PSX Stock Analysis - starting web interface...
echo  Browser will open at http://localhost:8501
echo  Keep this window open. Press Ctrl+C to stop.
echo.
"%PYTHON%" -m pip install -r requirements.txt -q
start "" "http://localhost:8501"
"%PYTHON%" -m streamlit run examples/stock_analysis_ui.py --server.headless true --server.port 8501 --server.address 0.0.0.0 --browser.gatherUsageStats false
if errorlevel 1 pause
