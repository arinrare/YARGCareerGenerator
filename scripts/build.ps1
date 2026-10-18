# build.ps1 — one-command build: fresh checkout -> portable distributable folder.
#
# Usage (from a PowerShell prompt, at the repository root):
#     .\scripts\build.ps1
#
# Output: dist\YARG Career Builder\  (fully self-contained, no user-folder access)

$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

$Venv   = Join-Path $Root ".venv"
$Python = Join-Path $Venv "Scripts\python.exe"

if (-not (Test-Path $Python)) {
    Write-Host "Creating virtual environment (Python $(python --version 2>&1))..."
    python -m venv $Venv
}

Write-Host "Installing dependencies from requirements.txt..."
& $Python -m pip install --upgrade pip | Out-Null
& $Python -m pip install -r (Join-Path $Root "requirements.txt")

Write-Host "Building with PyInstaller (one-folder)..."

# PyInstaller wipes dist\YARG Career Builder on rebuild. Stash the careers
# folder on the same drive (a rename, not a cross-drive copy) and restore it.
$Careers    = Join-Path $Root "dist\YARG Career Builder\careers"
$CareersBak = Join-Path $Root "dist\.careers_backup"
if (Test-Path $Careers) {
    if (Test-Path $CareersBak) { Remove-Item -Recurse -Force $CareersBak }
    Move-Item $Careers $CareersBak
}

& $Python -m PyInstaller (Join-Path $Root "packaging\yarg_career_builder.spec") --noconfirm --clean

if (Test-Path $CareersBak) {
    Move-Item $CareersBak $Careers
}

Write-Host ""
Write-Host "Build complete."
Write-Host "Output: $(Join-Path $Root 'dist\YARG Career Builder')"
Write-Host "Launch : dist\YARG Career Builder\YARG Career Builder.exe"
