@echo off
REM Live defence demo: one paired Static vs Dynamic comparison per scenario (a few seconds each).
cd /d "%~dp0"
if not exist .venv (
  echo Run RUN_SIMULATION.bat once first to set up Python packages.
  pause
  exit /b 1
)
call .venv\Scripts\activate.bat
echo.
echo ===== 1. BROWNOUT on Path A, 300 tps per branch =====
python demo.py --condition brownout --load 300
echo.
echo ===== 2. BLACKOUT on Path A, 300 tps per branch =====
python demo.py --condition blackout --load 300
echo.
echo ===== 3. STEADY STATE at congested load, 450 tps (flapping) =====
python demo.py --condition steady --load 450
pause
