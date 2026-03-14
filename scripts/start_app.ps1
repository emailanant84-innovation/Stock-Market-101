param(
  [switch]$SkipInstall
)

$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path -Parent $PSScriptRoot
$backendDir = Join-Path $repoRoot 'backend'
$frontendDir = Join-Path $repoRoot 'frontend'

function Test-CommandExists {
  param([string]$Command)
  return [bool](Get-Command $Command -ErrorAction SilentlyContinue)
}

if (-not (Test-CommandExists 'python')) {
  throw 'Python is not installed or not available in PATH.'
}

if (-not (Test-CommandExists 'npm')) {
  throw 'Node.js/npm is not installed or not available in PATH.'
}

Write-Host 'Starting India Stock AlphaScore app...' -ForegroundColor Cyan

# Backend setup
if (-not (Test-Path (Join-Path $backendDir '.venv'))) {
  Write-Host 'Creating backend virtual environment...' -ForegroundColor Yellow
  Push-Location $backendDir
  python -m venv .venv
  Pop-Location
}

if (-not $SkipInstall) {
  Write-Host 'Installing/upgrading backend dependencies...' -ForegroundColor Yellow
  Push-Location $backendDir
  & (Join-Path $backendDir '.venv\Scripts\python.exe') -m pip install --upgrade pip
  & (Join-Path $backendDir '.venv\Scripts\pip.exe') install -r requirements.txt
  Pop-Location

  Write-Host 'Installing frontend dependencies...' -ForegroundColor Yellow
  Push-Location $frontendDir
  npm install
  Pop-Location
}

# Start backend in separate terminal
$backendCommand = "cd /d `"$backendDir`" && .venv\Scripts\Activate.ps1; uvicorn main:app --host 0.0.0.0 --port 8000 --reload"
Start-Process powershell -ArgumentList '-NoExit', '-ExecutionPolicy', 'Bypass', '-Command', $backendCommand

# Start frontend in separate terminal
$frontendCommand = "cd /d `"$frontendDir`" && npm run dev"
Start-Process powershell -ArgumentList '-NoExit', '-ExecutionPolicy', 'Bypass', '-Command', $frontendCommand

Start-Sleep -Seconds 2
Start-Process 'http://localhost:5173'

Write-Host 'Launched backend and frontend terminals. Opening dashboard at http://localhost:5173' -ForegroundColor Green
Write-Host 'Tip: use .\\start_app.bat --skip-install for faster launches after initial setup.' -ForegroundColor Gray
