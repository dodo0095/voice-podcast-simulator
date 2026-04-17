@echo off
chcp 65001 > nul
echo ========================================
echo  修復 GPT-SoVITS 相依套件（Starlette 對齊）
echo ========================================
echo.
echo 症狀：啟動 webui.py 時出現
echo   ModuleNotFoundError: No module named 'starlette._exception_handler'
echo.
echo 策略：不寫死 starlette 版本，查目前 fastapi / gradio 要求，
echo       升級到兩者都接受的最低版本 ^(>=0.46, ^<2.0^)。
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
echo 升級 starlette 到 >=0.46.0,^<2.0（相容 FastAPI + 新版 Gradio）
echo ----------------------------------------
%PYTHON_EXE% -m pip install --upgrade "starlette>=0.46.0,<2.0"
if errorlevel 1 (
    echo [錯誤] 套件安裝失敗，請確認網路或 Python 路徑
    pause
    exit /b 1
)
echo.

echo ----------------------------------------
echo 驗證 _exception_handler 模組存在...
echo ----------------------------------------
%PYTHON_EXE% -c "from starlette import _exception_handler; print('[OK] starlette._exception_handler 可以匯入')"
if errorlevel 1 (
    echo [錯誤] 升級後仍無法匯入 _exception_handler，請手動檢查
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
