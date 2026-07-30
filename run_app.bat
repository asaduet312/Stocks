@echo off
setlocal
set "PYTHON=C:\Users\skt31\AppData\Local\Programs\Python\Python312\python.exe"
if not exist "%PYTHON%" (
    echo Python 3.12 not found. Install: winget install Python.Python.3.12
    pause
    exit /b 1
)
cd /d "%~dp0"
echo.
echo  PSX Stock Analysis - starting web interface...
echo  Browser will open at http://localhost:8501
echo  Keep this window open. Press Ctrl+C to stop.
echo.
"%PYTHON%" -m pip install streamlit plotly -q
start "" "http://localhost:8501"
"%PYTHON%" -m streamlit run examples/stock_analysis_ui.py --server.headless true --server.port 8501 --browser.gatherUsageStats false
if errorlevel 1 pause
