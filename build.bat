@echo off
setlocal EnableExtensions
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo Environment not found - running install.bat...
    call install.bat
    if errorlevel 1 exit /b 1
)

echo Building distributable...

rem PyInstaller wipes dist\YARG Career Builder on rebuild. Stash the careers
rem folder on the same drive (a rename, not a cross-drive copy) and restore it.
set "CAREERS=dist\YARG Career Builder\careers"
set "CAREERS_BAK=dist\.careers_backup"
if exist "%CAREERS%" (
    if exist "%CAREERS_BAK%" rmdir /s /q "%CAREERS_BAK%"
    move "%CAREERS%" "%CAREERS_BAK%" >nul
    if errorlevel 1 goto :error
)

".venv\Scripts\python.exe" -m PyInstaller packaging\yarg_career_builder.spec --noconfirm
if errorlevel 1 goto :error

if exist "%CAREERS_BAK%" (
    move "%CAREERS_BAK%" "%CAREERS%" >nul
)

echo.
echo Done. Output: dist\YARG Career Builder\YARG Career Builder.exe
pause
exit /b 0

:error
echo.
echo Build failed - see messages above.
pause
exit /b 1
