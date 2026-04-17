@echo off
chcp 65001 > nul
echo ========================================
echo  修復 FastAPI / Starlette / Gradio 版本衝突
echo ========================================
echo.
echo 症狀：啟動 webui.py 時出現
echo   ModuleNotFoundError: No module named 'starlette._exception_handler'
echo.
echo 原因：GPT-SoVITS requirements 與 gradio 版本不相容
echo.
echo ----------------------------------------
echo 顯示當前版本...
echo ----------------------------------------
python -m pip show fastapi starlette gradio 2>nul | findstr /i "Name: Version:"
echo.
echo ----------------------------------------
echo 升級至相容版本（fastapi 0.110+、starlette 0.36+、gradio 4.44+）
echo ----------------------------------------
python -m pip install --upgrade "fastapi>=0.110.0" "starlette>=0.36.3" "gradio>=4.44.0"
if errorlevel 1 (
    echo.
    echo [錯誤] 套件升級失敗，請確認：
    echo   1. Python 是否為 C:\py310 或其他預期路徑
    echo   2. 是否有網路連線
    echo   3. 是否需要 --user 或以系統管理員身分執行
    pause
    exit /b 1
)
echo.
echo ----------------------------------------
echo 升級後版本...
echo ----------------------------------------
python -m pip show fastapi starlette gradio 2>nul | findstr /i "Name: Version:"
echo.
echo ========================================
echo  修復完成！請重新執行 scripts\04_launch_training.bat
echo ========================================
pause
