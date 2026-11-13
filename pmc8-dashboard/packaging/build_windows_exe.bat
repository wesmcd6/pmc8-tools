@echo off
setlocal
cd /d "%~dp0\.."

echo ==============================================
echo Building PMC-8 Dashboard Standalone Windows EXE
echo ==============================================

set "PYTHON_CMD="
where py >nul 2>nul
if not errorlevel 1 set "PYTHON_CMD=py"
if not defined PYTHON_CMD (
    where python >nul 2>nul
    if not errorlevel 1 set "PYTHON_CMD=python"
)

if not defined PYTHON_CMD (
    echo Python was not found. Please install Python 3.10+
    pause
    exit /b 1
)

echo Installing build dependencies...
%PYTHON_CMD% -m pip install -r requirements.txt pyinstaller

echo Running PyInstaller to build a standalone single-file executable...
%PYTHON_CMD% -m PyInstaller --noconfirm --onefile --windowed --name "PMC8_Dashboard" --add-data "docs;docs" --add-data "p1load_package (1);p1load_package (1)" PMC8_Dashboard.py

if errorlevel 1 (
    echo Build failed.
    pause
    exit /b 1
)

echo.
echo Build succeeded! Standalone single-file executable is available at:
echo %CD%\dist\PMC8_Dashboard.exe
pause
