@echo off
title Deluzex Backend API Server
echo ===================================================
echo   Starting Deluzex Backend API (Port 8000)
echo ===================================================
cd /d "%~dp0"
call venv\Scripts\activate.bat
python -m uvicorn main:app --host 0.0.0.0 --port 8000
pause
