@echo off
chcp 65001 > nul
echo ========================================
echo  修復 GPT-SoVITS 相依套件（Starlette / Proxy）
echo ========================================
echo.
echo 症狀一：啟動 webui.py 時出現
echo   ModuleNotFoundError: No module named 'starlette._exception_handler'
echo 症狀二：Gradio TemplateResponse 相關錯誤
echo.
echo 正確解法：把 starlette 鎖定在 0.27.0（FastAPI 找得到、舊 Gradio 也能用）
echo.

:: 偵測 Python 路徑（優先用 C:\py310，其次用系統 python）
set PYTHON_EXE=
if exist "C:\py310\python.exe" (
    set PYTHON_EXE=C:\py310\python.exe
) else (
    where python >nul 2>&1
    if not errorlevel 1 (
        set PYTHON_EXE=python
    )
)

if "%PYTHON_EXE%"=="" (
    echo [錯誤] 找不到 Python，請確認安裝路徑
    pause
    exit /b 1
)
echo 使用 Python: %PYTHON_EXE%
echo.

echo ----------------------------------------
echo 當前版本...
echo ----------------------------------------
%PYTHON_EXE% -m pip show starlette fastapi gradio 2>nul | findstr /i "Name: Version:"
echo.

echo ----------------------------------------
echo 鎖定 starlette==0.27.0
echo ----------------------------------------
%PYTHON_EXE% -m pip install "starlette==0.27.0"
if errorlevel 1 (
    echo [錯誤] 套件安裝失敗，請確認網路或 Python 路徑
    pause
    exit /b 1
)
echo.

echo ----------------------------------------
echo 修復後版本...
echo ----------------------------------------
%PYTHON_EXE% -m pip show starlette fastapi gradio 2>nul | findstr /i "Name: Version:"
echo.

echo ========================================
echo  修復完成！請重新執行 scripts\04_launch_training.bat
echo ========================================
pause
