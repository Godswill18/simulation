@echo off
REM Runs the full 80-run experiment, sensitivity runs, analysis, figures and dashboard.
REM First run creates a private Python environment (.venv) and installs the packages.
cd /d "%~dp0"
where python >nul 2>nul
if errorlevel 1 (
  echo Python 3.10 or newer was not found. Install it from https://www.python.org/downloads/
  echo and tick "Add python.exe to PATH" during installation, then run this file again.
  pause
  exit /b 1
)
if not exist .venv (
  echo Creating Python environment...
  python -m venv .venv
)
call .venv\Scripts\activate.bat
echo Installing packages (first run only takes a minute)...
python -m pip install --quiet --upgrade pip
python -m pip install --quiet -r requirements.txt
python run_simulation.py %*
if errorlevel 1 (
  echo The simulation stopped with an error. See the messages above.
  pause
  exit /b 1
)
start "" "outputs\dashboard.html"
pause
