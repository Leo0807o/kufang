@echo off
chcp 65001 >nul
title Kufang Management System
cd /d %~dp0

set PORT=8000
if not "%~1"=="" set PORT=%~1

echo ========================================
echo   Kufang Management System
echo   http://%COMPUTERNAME%:%PORT%
echo   Ctrl+C to stop
echo ========================================
echo.

call .venv\Scripts\activate.bat

echo [1/3] Installing dependencies...
pip install -r requirements.txt -q
pip install waitress -q

echo [2/3] Collecting static files...
python manage.py collectstatic --noinput

echo [3/3] Starting server...
echo.
waitress-serve --host=0.0.0.0 --port=%PORT% --threads=8 config.wsgi:application

pause
