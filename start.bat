@echo off
chcp 65001 >nul
title Kufang - Dev Server
cd /d %~dp0

echo ========================================
echo   Kufang - Dev Server
echo   http://127.0.0.1:8000
echo   Ctrl+C to stop
echo ========================================
echo.

echo [1/4] Activating venv...
call .venv\Scripts\activate.bat

echo [2/4] Installing dependencies...
pip install -r requirements.txt -q

echo [3/4] Running migrations...
python manage.py migrate --run-syncdb

echo [4/4] Starting dev server...
echo.
python manage.py runserver

pause
