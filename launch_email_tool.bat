@echo off
title Deluzex Launch Email Tool
echo ===================================================
echo   de luzex - VIP Launch Email Broadcast Tool
echo ===================================================
cd /d "%~dp0"
call venv\Scripts\activate.bat
python send_launch_emails.py
echo.
pause
