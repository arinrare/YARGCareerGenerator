@echo off
setlocal EnableExtensions
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo Environment not found - running install.bat...
    call install.bat
    if errorlevel 1 exit /b 1
)

".venv\Scripts\python.exe" -m pytest
pause
exit /b %errorlevel%
