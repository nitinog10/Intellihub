$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$pythonExe = Join-Path $repoRoot ".venv\Scripts\python.exe"
$pytestExe = Join-Path $repoRoot ".venv\Scripts\pytest.exe"

if (-not (Test-Path $pythonExe)) {
    Write-Error "Virtual environment not found. Run scripts\setup_local.ps1 first."
}

Set-Location $repoRoot

Write-Host "Running pytest..." -ForegroundColor Cyan
& $pytestExe
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

Write-Host "Running compile sanity check..." -ForegroundColor Cyan
& $pythonExe -m compileall src main.py
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

Write-Host "All local checks completed." -ForegroundColor Green
