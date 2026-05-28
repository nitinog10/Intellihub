$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$pythonExe = Join-Path $repoRoot ".venv\Scripts\python.exe"

if (-not (Test-Path $pythonExe)) {
    Write-Error "Virtual environment not found. Run scripts\setup_local.ps1 first."
}

Set-Location $repoRoot
Write-Host "Starting ClosedLoop OS locally..." -ForegroundColor Cyan
Write-Host "  UI:     http://127.0.0.1:8000/" -ForegroundColor Green
Write-Host "  Docs:   http://127.0.0.1:8000/docs" -ForegroundColor Green
Write-Host "  Health: http://127.0.0.1:8000/healthz" -ForegroundColor Green
Write-Host "  MCP:    http://127.0.0.1:8000/mcp" -ForegroundColor Green
Write-Host ""
& $pythonExe "main.py"
