# PyScreenshot 打包脚本 (PowerShell)
# 使用方法: 右键 -> 使用 PowerShell 运行

$ErrorActionPreference = "Stop"

Write-Host "========================================"
Write-Host "  PyScreenshot 打包脚本"
Write-Host "========================================"
Write-Host ""

# 检查 Python
try {
    $pythonVersion = python --version 2>&1
    Write-Host "[OK] Python: $pythonVersion"
} catch {
    Write-Host "[错误] 未找到 Python，请先安装 Python 3.8+"
    Write-Host "下载地址: https://www.python.org/downloads/"
    Read-Host "按回车键退出"
    exit 1
}

# 安装依赖
Write-Host ""
Write-Host "[1/5] 安装依赖..."
python -m pip install -r requirements.txt -q
python -m pip install pyinstaller -q

# 清理旧文件
Write-Host "[2/5] 清理旧文件..."
if (Test-Path "dist") { Remove-Item -Recurse -Force "dist" }
if (Test-Path "build") { Remove-Item -Recurse -Force "build" }

# 打包更新程序
Write-Host "[3/5] 打包更新程序 (updater.exe)..."
# 注意: 如果 updater.spec 存在，优先使用 spec 文件
if (Test-Path "updater.spec") {
    python -m PyInstaller updater.spec --clean --noconfirm
} else {
    python -m PyInstaller --onefile --noconsole --name updater --icon "截图贴图工具图标.ico" updater.py
}

if (-not (Test-Path "dist\updater.exe")) {
    Write-Host "[错误] updater.exe 打包失败"
    Read-Host "按回车键退出"
    exit 1
}

# 打包主程序
Write-Host "[4/5] 打包主程序..."
if (Test-Path "app.spec") {
    python -m PyInstaller app.spec --clean --noconfirm
} else {
    python -m PyInstaller --onefile --noconsole --name "截图贴图工具" --icon "截图贴图工具图标.ico" main.py
}

# 整合文件
Write-Host "[5/5] 整合文件..."
if (-not (Test-Path "dist\截图贴图工具")) {
    New-Item -ItemType Directory -Path "dist\截图贴图工具" -Force
}

# 将 dist 中的文件移动到 截图贴图工具 子目录 (如果不是单文件模式)
if (Test-Path "dist\main") {
    Move-Item "dist\main\*" "dist\截图贴图工具\" -Force
}

if (Test-Path "dist\updater.exe") {
    Copy-Item "dist\updater.exe" "dist\截图贴图工具\" -Force
}

# 检查结果
Write-Host ""
if (Test-Path "dist\截图贴图工具\截图贴图工具.exe") {
    $fileSize = (Get-Item "dist\截图贴图工具\截图贴图工具.exe").Length / 1MB
    Write-Host "========================================"
    Write-Host "  打包成功!"
    Write-Host "  输出目录: dist\截图贴图工具"
    Write-Host "  主程序大小: $([math]::Round($fileSize, 2)) MB"
    Write-Host "========================================"
} else {
    Write-Host "[错误] 打包失败，请检查错误信息"
}

Write-Host ""
# Read-Host "按回车键退出" # 在非交互式环境中注释掉
