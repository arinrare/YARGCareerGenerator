# run.ps1 — run the GUI from source (dev workflow).
#
# Usage:
#     .\scripts\run.ps1
#
# If no virtual environment exists it is created and dependencies are installed.

$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

$Venv   = Join-Path $Root ".venv"
$Python = Join-Path $Venv "Scripts\python.exe"

if (-not (Test-Path $Python)) {
    Write-Host "Creating virtual environment..."
    python -m venv $Venv
    & $Python -m pip install --upgrade pip | Out-Null
    & $Python -m pip install -r (Join-Path $Root "requirements.txt")
}

$env:PYTHONPATH = (Join-Path $Root "src")
& $Python -m yarg_career_builder
