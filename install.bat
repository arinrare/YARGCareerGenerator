@echo off
setlocal EnableExtensions
cd /d "%~dp0"

set "PY=python"
where python >nul 2>nul || set "PY=py -3"

if not exist ".venv\Scripts\python.exe" (
    echo Creating virtual environment...
    %PY% -m venv .venv
    if errorlevel 1 goto :error
)

echo Installing dependencies from requirements.txt...
".venv\Scripts\python.exe" -m pip install --upgrade pip >nul
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 goto :error

echo.
echo Dependencies installed.
pause
exit /b 0

:error
echo.
echo Install failed - see messages above.
pause
exit /b 1
