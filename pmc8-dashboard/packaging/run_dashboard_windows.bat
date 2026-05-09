@echo off
setlocal
cd /d "%~dp0\PMC8_Dashboard_Windows"

set "PYTHON_CMD="
where py >nul 2>nul
if not errorlevel 1 set "PYTHON_CMD=py"

if not defined PYTHON_CMD (
    where python >nul 2>nul
    if not errorlevel 1 set "PYTHON_CMD=python"
)

if not defined PYTHON_CMD (
    where python3 >nul 2>nul
    if not errorlevel 1 set "PYTHON_CMD=python3"
)

if not defined PYTHON_CMD (
    echo Python was not found.
    echo.
    echo Install Python 3.10 or newer from https://www.python.org/downloads/windows/
    echo During installation, enable "Add python.exe to PATH".
    echo.
    echo Administrator mode is normally not required. Open a new Command Prompt after installing Python.
    pause
    exit /b 1
)

echo Using Python command: %PYTHON_CMD%
%PYTHON_CMD% -m pip install -r requirements.txt
if errorlevel 1 (
    echo.
    echo Failed to install Python requirements.
    pause
    exit /b 1
)

%PYTHON_CMD% PMC8_Dashboard.py
pause
