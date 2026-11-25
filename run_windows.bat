@echo off
setlocal
cd /d "%~dp0"
title Tourism Package Planner - Windows Launcher

echo ================================================
echo       TOURISM PACKAGE PLANNER
echo ================================================
echo.

where py >nul 2>nul
if errorlevel 1 goto no_python

if not exist ".venv\Scripts\python.exe" (
    echo [1/3] Creating Python virtual environment...
    py -3 -m venv .venv
    if errorlevel 1 goto setup_error
) else (
    echo [1/3] Virtual environment already exists.
)

echo.
echo [2/3] Installing/checking required packages...
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 goto setup_error

echo.
echo [3/3] Starting the application...
echo Open this address in your browser: http://127.0.0.1:5000
echo Keep this window open while using the project.
echo Press Ctrl+C here to stop the server.
echo.
".venv\Scripts\python.exe" app.py

echo.
echo The application has stopped.
pause
exit /b 0

:no_python
echo ERROR: Python 3 was not found.
echo Install Python 3.10 or newer from https://www.python.org/downloads/windows/
echo During installation, tick the checkbox: Add python.exe to PATH.
echo Then close and reopen this window and run this file again.
pause
exit /b 1

:setup_error
echo.
echo ERROR: Setup failed. Check your internet connection and Python installation.
echo You can also follow the manual steps in README.md.
pause
exit /b 1
