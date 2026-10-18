@echo off
setlocal EnableExtensions
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo Environment not found - running install.bat...
    call install.bat
    if errorlevel 1 exit /b 1
)

set "PYTHONPATH=%~dp0src"
start "" ".venv\Scripts\pythonw.exe" -m yarg_career_builder
exit /b 0
