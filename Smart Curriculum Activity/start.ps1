# Smart Curriculum Activity & Attendance Management App Bootstrapper
# Set terminal encoding to UTF-8 for clean logs
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host "       EduSmart - Smart Curriculum & Attendance Management App        " -ForegroundColor Cyan
Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host ""

# 1. Verify Python
Write-Host "1. Verifying Python installation..." -ForegroundColor Yellow
$pythonCheck = Get-Command python -ErrorAction SilentlyContinue
if (-not $pythonCheck) {
    Write-Error "Python is not installed or not in system PATH. Please install Python 3.7+."
    Exit
}
$pythonVersion = python --version
Write-Host "   Active: $pythonVersion" -ForegroundColor Green

# 2. Initialize Database if not already present
Write-Host "2. Checking database state..." -ForegroundColor Yellow
$dbFile = Join-Path $PSScriptRoot "backend\curriculum_tracker.db"
if (-not (Test-Path $dbFile)) {
    Write-Host "   Database file not found. Initializing database and seeding records..." -ForegroundColor Cyan
    python backend/database.py
} else {
    Write-Host "   Database file found at: backend/curriculum_tracker.db" -ForegroundColor Green
}

# 3. Configure PYTHONPATH environment variable
Write-Host "3. Configuring PYTHONPATH..." -ForegroundColor Yellow
$env:PYTHONPATH = "backend"
Write-Host "   PYTHONPATH set to 'backend'" -ForegroundColor Green

# 4. Open Web Browser
Write-Host "4. Opening browser link in 2 seconds..." -ForegroundColor Yellow
Start-Sleep -Seconds 2
Start-Process "http://127.0.0.1:5000/"

# 5. Start Flask Backend
Write-Host "5. Launching Flask Web Server at: http://127.0.0.1:5000/" -ForegroundColor Cyan
Write-Host "   (Press Ctrl+C inside this window to stop the server)" -ForegroundColor Yellow
Write-Host ""

python backend/main.py
