$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$venvPath = Join-Path $repoRoot ".venv"
$pythonExe = Join-Path $venvPath "Scripts\python.exe"
$pipExe = Join-Path $venvPath "Scripts\pip.exe"
$sampleSettings = Join-Path $repoRoot "local.settings.sample.json"
$localSettings = Join-Path $repoRoot "local.settings.json"

Write-Host "Setting up ClosedLoop OS locally..." -ForegroundColor Cyan

if (-not (Test-Path $venvPath)) {
    Write-Host "Creating virtual environment at .venv" -ForegroundColor Yellow
    python -m venv $venvPath
}

Write-Host "Upgrading pip inside .venv" -ForegroundColor Yellow
& $pythonExe -m pip install --upgrade pip

Write-Host "Installing project dependencies" -ForegroundColor Yellow
& $pipExe install -e ".[dev]"

if (-not (Test-Path $localSettings)) {
    Write-Host "Creating local.settings.json from sample" -ForegroundColor Yellow
    Copy-Item $sampleSettings $localSettings
} else {
    Write-Host "local.settings.json already exists, leaving it as-is" -ForegroundColor DarkYellow
}

Write-Host ""
Write-Host "Local setup complete." -ForegroundColor Green
Write-Host "Next commands:" -ForegroundColor Green
Write-Host "  .\.venv\Scripts\Activate.ps1"
Write-Host "  python main.py"
Write-Host "  pytest"
