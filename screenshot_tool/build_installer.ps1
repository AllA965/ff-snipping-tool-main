# PyScreenshot Package Script
# Includes: PyInstaller + Inno Setup

$ErrorActionPreference = "Stop"

Write-Host "========================================"
Write-Host "  Preparing packaging environment..."
Write-Host "========================================"
Write-Host ""

# 1. Check Python
try {
    $pythonVersion = python --version 2>&1
    Write-Host "[OK] Python: $pythonVersion"
} catch {
    Write-Host "[Error] Python not found. Please install Python 3.8+"
    exit 1
}

# 2. Install dependencies
Write-Host "[1/6] Installing dependencies..."
python -m pip install -r requirements.txt -q
python -m pip install pyinstaller -q

# 3. Clean old files
Write-Host "[2/6] Cleaning old files..."
if (Test-Path "dist") { Remove-Item -Recurse -Force "dist" }
if (Test-Path "build") { Remove-Item -Recurse -Force "build" }
if (Test-Path "dist_installer") { Remove-Item -Recurse -Force "dist_installer" }

# 4. Package updater.exe
Write-Host "[3/6] Packaging updater.exe..."
python -m PyInstaller --onefile --noconsole --name updater --icon "app_icon.ico" updater.py
if (-not (Test-Path "dist\updater.exe")) {
    Write-Host "[Error] updater.exe packaging failed"
    exit 1
}

# 5. Package main application
Write-Host "[4/6] Packaging main app with spec file..."
python -m PyInstaller app.spec --clean --noconfirm

# 6. Merge files
Write-Host "[5/6] Merging updater and main app..."
if (Test-Path "dist\updater.exe") {
    if (-not (Test-Path "dist\PyScreenshot")) {
        New-Item -ItemType Directory -Path "dist\PyScreenshot" -Force
    }
    Copy-Item "dist\updater.exe" "dist\PyScreenshot\"
}

# 7. Run Inno Setup
Write-Host "[6/6] Generating installer (Inno Setup)..."
$isccPath = "C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
if (Test-Path $isccPath) {
    & $isccPath "installer.iss"
    Write-Host ""
    Write-Host "========================================"
    Write-Host "  Packaging successful!"
    Write-Host "  Installer location: dist_installer\"
    Write-Host "========================================"
} else {
    Write-Host ""
    Write-Host "[Warning] Inno Setup 6 not found."
    Write-Host "Please manually run Inno Setup on 'installer.iss'."
    Write-Host "Main app generated in: dist\PyScreenshot\"
}

Write-Host ""
Write-Host "Finished."
