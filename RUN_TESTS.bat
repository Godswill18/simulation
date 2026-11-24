@echo off
REM Model validation tests (queueing maths, fairness, reproducibility, availability formula).
cd /d "%~dp0"
call .venv\Scripts\activate.bat
python tests\test_model.py
pause
