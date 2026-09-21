@echo off
setlocal
cd /d "%~dp0"
python --version >nul 2>&1
if errorlevel 1 (
  echo Install Python 3.10 or newer from python.org and enable Add Python to PATH.
  pause
  exit /b 1
)
python -m venv .venv
if errorlevel 1 goto failed
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 goto failed
".venv\Scripts\python.exe" -m playwright install chromium
if errorlevel 1 goto failed
echo Setup complete. Double-click Start.cmd to open the app.
pause
exit /b 0
:failed
echo Setup failed. Check the error above and your internet connection.
pause
exit /b 1
