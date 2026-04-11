@echo off
chcp 65001 > nul
echo ========================================
echo  Step 4: 啟動 GPT-SoVITS 訓練介面
echo ========================================
echo.

cd /d "%~dp0\.."
set PROJECT_ROOT=%CD%
set DATASET_LIST=%PROJECT_ROOT%\data\transcripts\dataset_validated.txt

:: 確認資料集存在
if not exist "%DATASET_LIST%" (
    echo [錯誤] 找不到驗證後的資料集: %DATASET_LIST%
    echo 請先執行 Step 3: python scripts\03_validate_dataset.py
    pause
    exit /b 1
)

:: 計算資料筆數
for /f %%c in ('find /c /v "" "%DATASET_LIST%"') do set LINE_COUNT=%%c
echo 訓練資料: %LINE_COUNT% 筆

:: 確認 GPT-SoVITS 存在
if not exist "GPT-SoVITS" (
    echo [錯誤] 找不到 GPT-SoVITS 資料夾
    echo 請先執行: setup\install.bat
    pause
    exit /b 1
)

echo.
echo ========================================
echo  訓練流程說明（WebUI 操作）
echo ========================================
echo.
echo 即將啟動 GPT-SoVITS WebUI
echo 請依照以下步驟操作：
echo.
echo 【1. 訓練 SoVITS 模型】
echo   - 切換到「SoVITS 訓練」分頁
echo   - 「訓練列表路徑」填入:
echo     %DATASET_LIST%
echo   - 「實驗名稱」填入: my_voice
echo   - Epoch 設定: 8（資料多可設 16）
echo   - 點擊「一鍵三連」開始訓練
echo.
echo 【2. 訓練 GPT 模型】
echo   - 切換到「GPT 訓練」分頁
echo   - 同樣填入訓練列表路徑
echo   - Epoch 設定: 15
echo   - 點擊開始訓練
echo.
echo 【3. 訓練完成後】
echo   - 找到訓練產生的 .pth 和 .ckpt 檔案
echo   - 複製到 models\ 資料夾
echo   - 更新 configs\voice_config.yaml 中的模型路徑
echo.
echo ========================================
echo.
pause

:: 啟動 GPT-SoVITS WebUI
cd GPT-SoVITS
echo 啟動 GPT-SoVITS...
python webui.py

pause
