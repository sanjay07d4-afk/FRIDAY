@echo off
echo ========================================================
echo Starting FRIDAY AI Production Backend Service...
echo ========================================================

cd /d "%~dp0\.."

if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
)

python scripts\run.py
pause
