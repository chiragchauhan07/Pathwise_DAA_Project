# ==============================================================================
# Pathwise - Local Development Startup Script (PowerShell)
# Starts the FastAPI Backend (Port 8000) and Vite React Frontend (Port 5173)
# ==============================================================================

[CmdletBinding()]
param(
    [int]$BackendPort = 8000,
    [int]$FrontendPort = 5173,
    [switch]$SkipInstall
)

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
Set-Location $ScriptDir

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "   Pathwise: Course Learning Path Generator Launcher     " -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

# 1. Check Python
$PythonCmd = $null
if (Test-Path "$ScriptDir\venv\Scripts\python.exe") {
    $PythonCmd = "$ScriptDir\venv\Scripts\python.exe"
    Write-Host "[✓] Found virtual environment at .\venv" -ForegroundColor Green
} elseif (Test-Path "$ScriptDir\.venv\Scripts\python.exe") {
    $PythonCmd = "$ScriptDir\.venv\Scripts\python.exe"
    Write-Host "[✓] Found virtual environment at .\.venv" -ForegroundColor Green
} else {
    $SysPython = Get-Command python -ErrorAction SilentlyContinue
    if ($SysPython) {
        $PythonCmd = "python"
        Write-Host "[!] Virtual environment not detected; using system python: $($SysPython.Source)" -ForegroundColor Yellow
    } else {
        Write-Error "Python 3.12+ is required but was not found on PATH or in .\venv."
        exit 1
    }
}

# 2. Check Node & npm
$NodeCmd = Get-Command node -ErrorAction SilentlyContinue
$NpmCmd = Get-Command npm -ErrorAction SilentlyContinue
if (-not $NodeCmd -or -not $NpmCmd) {
    Write-Error "Node.js (18+) and npm are required but were not found on PATH."
    exit 1
}
Write-Host "[✓] Found Node.js: $(node -v) and npm: $(npm -v)" -ForegroundColor Green

# 3. Check .env
if (-not (Test-Path "$ScriptDir\.env")) {
    if (Test-Path "$ScriptDir\.env.example") {
        Copy-Item "$ScriptDir\.env.example" "$ScriptDir\.env"
        Write-Host "[✓] Created .env from .env.example" -ForegroundColor Green
    }
}

# 3b. Check Python Dependencies
if (-not $SkipInstall) {
    $MissingDeps = $false
    try {
        & $PythonCmd -c "import fastapi, uvicorn, google.genai, dotenv" 2>$null
        if ($LASTEXITCODE -ne 0) { $MissingDeps = $true }
    } catch {
        $MissingDeps = $true
    }
    if ($MissingDeps) {
        Write-Host "[*] Installing Python backend dependencies from requirements.txt..." -ForegroundColor Yellow
        & $PythonCmd -m pip install -r "$ScriptDir\requirements.txt" --quiet
        Write-Host "[✓] Python dependencies installed successfully" -ForegroundColor Green
    } else {
        Write-Host "[✓] Python dependencies verified" -ForegroundColor Green
    }
}

# 4. Check Frontend Dependencies
$FrontendDir = "$ScriptDir\final_frontend"
if (-not (Test-Path "$FrontendDir\node_modules") -and -not $SkipInstall) {
    Write-Host "[*] Installing frontend dependencies in final_frontend..." -ForegroundColor Yellow
    Push-Location $FrontendDir
    try {
        & npm install
    } finally {
        Pop-Location
    }
}

# 5. Launch Backend and Frontend Background Jobs
Write-Host "`n[*] Starting FastAPI Backend on port $BackendPort..." -ForegroundColor Cyan
$BackendScript = {
    param($Dir, $Python, $Port, $ApiKey, $Model)
    Set-Location $Dir
    $env:PYTHONPATH = $Dir
    if ($ApiKey) { $env:GEMINI_API_KEY = $ApiKey }
    if ($Model) { $env:GEMINI_MODEL = $Model }
    & $Python -m uvicorn backend.core_engine.main:app --host 127.0.0.1 --port $Port
}
$BackendJob = Start-Job -ScriptBlock $BackendScript -ArgumentList $ScriptDir, $PythonCmd, $BackendPort, $env:GEMINI_API_KEY, $env:GEMINI_MODEL

Write-Host "[*] Starting Vite React Frontend on port $FrontendPort..." -ForegroundColor Cyan
$FrontendScript = {
    param($FDir, $Port)
    Set-Location $FDir
    & npm run dev -- --port $Port --host 127.0.0.1
}
$FrontendJob = Start-Job -ScriptBlock $FrontendScript -ArgumentList $FrontendDir, $FrontendPort

# 6. Wait for servers to spin up
Start-Sleep -Seconds 3

Write-Host "`n==========================================================" -ForegroundColor Green
Write-Host "   Pathwise is running!" -ForegroundColor Green
Write-Host "==========================================================" -ForegroundColor Green
Write-Host "   Frontend Application: http://localhost:$FrontendPort" -ForegroundColor White
Write-Host "   FastAPI Documentation: http://127.0.0.1:$BackendPort/docs" -ForegroundColor White
Write-Host "   Backend Health Check: http://127.0.0.1:$BackendPort/api/v1/health" -ForegroundColor White
Write-Host "`nPress Ctrl+C to stop both servers.`n" -ForegroundColor Yellow

try {
    while ($true) {
        # Check job statuses
        if ($BackendJob.State -ne "Running") {
            Write-Host "`n[!] Backend job stopped unexpectedly:" -ForegroundColor Red
            Receive-Job -Job $BackendJob
            break
        }
        if ($FrontendJob.State -ne "Running") {
            Write-Host "`n[!] Frontend job stopped unexpectedly:" -ForegroundColor Red
            Receive-Job -Job $FrontendJob
            break
        }
        Start-Sleep -Seconds 1
    }
} finally {
    Write-Host "`nStopping Pathwise servers..." -ForegroundColor Yellow
    Stop-Job -Job $BackendJob -ErrorAction SilentlyContinue
    Remove-Job -Job $BackendJob -Force -ErrorAction SilentlyContinue
    Stop-Job -Job $FrontendJob -ErrorAction SilentlyContinue
    Remove-Job -Job $FrontendJob -Force -ErrorAction SilentlyContinue
    Write-Host "Both servers stopped successfully." -ForegroundColor Green
}

