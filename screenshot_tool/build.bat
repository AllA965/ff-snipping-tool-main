@echo off
chcp 65001 >nul
echo ========================================
echo   截图贴图工具 打包脚本 (含自动更新)
echo ========================================
echo.

:: 尝试找到 Python
where py >nul 2>&1
if %errorlevel%==0 (
    set PYTHON=py -3
    goto :found_python
)

where python >nul 2>&1
if %errorlevel%==0 (
    set PYTHON=python
    goto :found_python
)

echo [错误] 未找到 Python，请先安装 Python 3.8+
echo 下载地址: https://www.python.org/downloads/
pause
exit /b 1

:found_python
echo [OK] 使用 Python: %PYTHON%
%PYTHON% --version

:: 安装依赖
echo.
echo [1/5] 安装依赖...
%PYTHON% -m pip install -r requirements.txt -q
%PYTHON% -m pip install pyinstaller -q

:: 清理旧的构建文件
echo [2/5] 清理旧文件...
if exist "dist" rmdir /s /q dist
if exist "build" rmdir /s /q build

:: 打包更新程序
echo [3/5] 打包更新程序 (updater.exe)...
%PYTHON% -m PyInstaller updater.spec --clean --noconfirm
if not exist "dist\updater.exe" (
    echo [错误] updater.exe 打包失败
    pause
    exit /b 1
)

:: 打包主程序
echo [4/5] 打包主程序...
%PYTHON% -m PyInstaller app.spec --clean --noconfirm

:: 整合文件
echo [5/5] 整合文件...
if not exist "dist\截图贴图工具" mkdir "dist\截图贴图工具"
copy "dist\updater.exe" "dist\截图贴图工具\" >nul

:: 检查结果
if exist "dist\截图贴图工具\截图贴图工具.exe" (
    echo.
    echo ========================================
    echo   打包成功！
    echo   输出目录: dist\截图贴图工具
    echo ========================================
) else (
    echo.
    echo [错误] 打包失败，请检查错误信息
)

echo.
pause
