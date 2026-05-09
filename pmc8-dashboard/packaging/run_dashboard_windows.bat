@echo off
setlocal
cd /d "%~dp0\PMC8_Dashboard_Windows"
py -m pip install -r requirements.txt
py PMC8_Dashboard.py
pause
