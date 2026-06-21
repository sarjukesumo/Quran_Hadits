$host.ui.RawUI.WindowTitle = "Tuyul Dataset Bot — Setup"

Write-Host "=== Tuyul Dataset Bot Setup ===" -ForegroundColor Cyan

# check python
$ver = python --version 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Python not found. Install Python 3.11+ from python.org" -ForegroundColor Red
    exit 1
}
Write-Host "Python: $ver" -ForegroundColor Green

# venv
if (-not (Test-Path ".venv")) {
    Write-Host "Creating virtual environment ..." -ForegroundColor Yellow
    python -m venv .venv
}
Write-Host "[OK] .venv" -ForegroundColor Green

# install deps
& ".venv\Scripts\pip" install -r requirements.txt
if ($LASTEXITCODE -eq 0) {
    Write-Host "[OK] Dependencies installed" -ForegroundColor Green
} else {
    Write-Host "ERROR: pip install failed" -ForegroundColor Red
    exit 1
}

# .env
if (-not (Test-Path ".env")) {
    Copy-Item ".env.example" ".env"
    Write-Host "[OK] .env created — edit with your HF credentials" -ForegroundColor Green
} else {
    Write-Host "[SKIP] .env already exists" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "Setup complete!" -ForegroundColor Cyan
Write-Host "To run  : .venv\Scripts\python bot.py" -ForegroundColor White
Write-Host "To stop : Ctrl+C" -ForegroundColor White
