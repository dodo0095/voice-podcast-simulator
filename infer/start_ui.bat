@echo off
chcp 65001 > nul
echo ========================================
echo  AI 聲音克隆 — 啟動 Web UI
echo ========================================
echo.
echo 瀏覽器將自動開啟 http://localhost:7860
echo 關閉此視窗即停止服務
echo.
cd /d "%~dp0\.."
python infer\infer_ui.py
pause
