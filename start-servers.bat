@echo off
title ExplorestarsLite Server

:: Set working directory to wherever this bat file lives
cd /d "%~dp0"

echo.
echo  ============================================
echo   ExplorestarsLite PWA Server
echo  ============================================
echo.

:: Check prerequisites
where node >nul 2>&1
if %errorlevel% neq 0 (
    echo  ERROR: Node.js not found.
    echo         Install it from: https://nodejs.org
    echo         Click the big green LTS button, run the installer.
    echo.
    pause
    exit /b 1
)

if not exist "C:\caddy\caddy.exe" (
    echo  ERROR: Caddy not found at C:\caddy\caddy.exe
    echo         Download from: https://caddyserver.com/download
    echo         Select Windows amd64, download, rename to caddy.exe
    echo         Put it in C:\caddy\
    echo.
    pause
    exit /b 1
)

if not exist "wwwroot\index.html" (
    echo  ERROR: wwwroot folder not found.
    echo         Make sure this bat file is in the same folder
    echo         as the wwwroot folder, Caddyfile, and mount-proxy.js
    echo.
    pause
    exit /b 1
)

:: Get PC IP address
set PC_IP=unknown
for /f "tokens=2 delims=:" %%a in ('ipconfig ^| findstr /c:"IPv4 Address" ^| findstr /v "127.0.0"') do (
    set PC_IP=%%a
)
set PC_IP=%PC_IP: =%

echo  Prerequisites OK
echo.
echo  Your PC IP address: %PC_IP%
echo.
echo  Starting servers...
echo.

:: Start mount proxy (Node.js) in background
echo  [1/2] Starting mount proxy...
start /min "ExplorestarsLite-MountProxy" node mount-proxy.js

:: Start Caddy (serves app + HTTPS) in background
echo  [2/2] Starting web server...
start /min "ExplorestarsLite-Caddy" C:\caddy\caddy.exe run --config Caddyfile --adapter caddyfile

:: Wait for Caddy to generate its certificate
timeout /t 3 /nobreak >nul

:: Generate the iPhone HTTPS certificate profile (first run only)
if not exist "wwwroot\caddy-trust.mobileconfig" (
    node generate-mobileconfig.js
)

echo.
echo  ============================================
echo   All servers started!
echo  ============================================
echo.
echo   Open this address on your phone's browser:
echo.
echo      http://%PC_IP%:5257
echo.
echo   For HTTPS (polar alignment on iPhone):
echo.
echo      https://%PC_IP%:5256
echo.
echo      (Requires certificate install — see docs folder)
echo.
echo  ============================================
echo   Press any key to STOP the servers...
echo  ============================================
pause >nul

:: Kill all server processes
echo.
echo  Stopping servers...
taskkill /fi "windowtitle eq ExplorestarsLite-MountProxy" /f >nul 2>&1
taskkill /fi "windowtitle eq ExplorestarsLite-Caddy" /f >nul 2>&1
echo  All servers stopped.
timeout /t 2 /nobreak >nul
