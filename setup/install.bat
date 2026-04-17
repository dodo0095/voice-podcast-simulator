@echo off
chcp 65001 > nul
echo ========================================
echo  AI 聲音克隆系統 — 一鍵安裝
echo ========================================
echo.

:: 檢查 Python
python --version > nul 2>&1
if errorlevel 1 (
    echo [錯誤] 找不到 Python！請先安裝 Python 3.10
    echo 下載: https://www.python.org/downloads/release/python-31011/
    pause
    exit /b 1
)

for /f "tokens=2" %%v in ('python --version 2^>^&1') do set PYVER=%%v
echo [OK] Python 版本: %PYVER%

:: 檢查 Git
git --version > nul 2>&1
if errorlevel 1 (
    echo [錯誤] 找不到 Git！請先安裝 Git
    echo 下載: https://git-scm.com/download/win
    pause
    exit /b 1
)
echo [OK] Git 已安裝

:: 回到專案根目錄
cd /d "%~dp0\.."
set PROJECT_ROOT=%CD%

echo.
echo [步驟 1/4] 安裝前處理相依套件...
pip install -r setup\requirements-preprocess.txt
if errorlevel 1 (
    echo [錯誤] 套件安裝失敗
    pause
    exit /b 1
)
echo [OK] 前處理套件安裝完成

echo.
echo [步驟 2/4] 下載 GPT-SoVITS...
if not exist "GPT-SoVITS" (
    git clone https://github.com/RVC-Boss/GPT-SoVITS.git
    if errorlevel 1 (
        echo [錯誤] 下載 GPT-SoVITS 失敗，請確認網路連線
        pause
        exit /b 1
    )
    echo [OK] GPT-SoVITS 下載完成
) else (
    echo [跳過] GPT-SoVITS 已存在
)

echo.
echo [步驟 3/4] 安裝 GPT-SoVITS 相依套件...
cd GPT-SoVITS
pip install -r requirements.txt
if errorlevel 1 (
    echo [警告] 部分套件安裝失敗，請手動確認
)
cd ..
echo [OK] GPT-SoVITS 套件安裝完成

echo.
echo [步驟 4/4] 安裝推論介面套件...
pip install gradio>=4.0.0 pyyaml colorama
echo [OK] 推論套件安裝完成

echo.
echo ========================================
echo  安裝完成！
echo ========================================
echo.
echo 接下來的步驟：
echo   1. 把你的 MP3 檔案放到 data\raw\ 資料夾
echo   2. 執行: python scripts\01_preprocess.py
echo   3. 執行: python scripts\02_transcribe.py
echo   4. 執行: python scripts\03_validate_dataset.py  （校稿）
echo   5. 執行: python scripts\04_launch_training.bat   （開始訓練）
echo   6. 訓練完後執行: python infer\infer_ui.py         （使用介面）
echo.
echo 詳細說明請閱讀 QUICK_START.md
echo.
pause
