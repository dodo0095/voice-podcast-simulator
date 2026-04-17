@echo off
chcp 65001 > nul
echo ========================================
echo  Step 4: 啟動 GPT-SoVITS 訓練介面
echo ========================================
echo.

cd /d "%~dp0\.."
set PROJECT_ROOT=%CD%
set DATASET_LIST=%PROJECT_ROOT%\data\transcripts\dataset_validated.txt

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
echo 請依照順序操作，別跳步（跳步會看到「23456 開頭檔案不存在」錯誤）：
echo.
echo 【1. 切到「1-GPT-SoVITS-TTS」分頁，填頂部欄位】
echo   - 實驗名 (experiment_name):      my_voice
echo   - 標註文件路徑 (inp_text):
echo     %DATASET_LIST%
echo   - 音頻切片目錄 (inp_wav_dir):
echo     %PROJECT_ROOT%\data\sliced
echo   - GPU 編號:                     0
echo.
echo 【2. 切「1A-訓練集格式化工具」子分頁，按「一鍵三連」】
echo   - 會依序跑：1Aa 文本獲取 → 1Ab SSL 特徵 → 1Ac 語義特徵
echo   - 完成後 GPT-SoVITS\logs\my_voice\ 會有：
echo       2-name2text.txt、3-bert\、4-cnhubert\、5-wav32k\、6-name2semantic.tsv
echo   - 這一步完成後才能訓練，不做會報「23456 檔案不存在」
echo.
echo 【3. 切「1B-SoVITS 訓練」子分頁】
echo   - Epoch 設定: 8（資料多可設 16）
echo   - 點擊「開始 SoVITS 訓練」
echo.
echo 【4. 切「1C-GPT 訓練」子分頁】
echo   - Epoch 設定: 15
echo   - 點擊「開始 GPT 訓練」
echo.
echo 【5. 訓練完成後】
echo   - 找到訓練產生的 .pth 和 .ckpt 檔案
echo   - 複製到 models\ 資料夾
echo   - 更新 configs\voice_config.yaml 中的模型路徑
echo.
echo ========================================
echo.
pause

:: 檢查 Starlette 是否有 FastAPI 需要的 _exception_handler 模組
:: 不寫死版本，只在缺模組時升級到 FastAPI / Gradio 雙方都接受的最低版 (>=0.46,<2.0)
echo 檢查 Starlette 相容性...
%PYTHON_EXE% -c "from starlette import _exception_handler" 2>nul
if errorlevel 1 (
    echo [修復] Starlette 缺少 _exception_handler 模組，升級中...
    %PYTHON_EXE% -m pip install "starlette>=0.46.0,<2.0" --quiet
    if errorlevel 1 (
        echo [錯誤] Starlette 升級失敗
        pause
        exit /b 1
    )
    echo [完成] Starlette 已升級
) else (
    echo [OK] Starlette 相容
)

:: 清除 Proxy 設定（避免 Gradio 無法綁定 localhost）
set HTTP_PROXY=
set HTTPS_PROXY=
set http_proxy=
set https_proxy=
set NO_PROXY=localhost,127.0.0.1
set no_proxy=localhost,127.0.0.1

:: 啟動 GPT-SoVITS WebUI
cd GPT-SoVITS
echo 啟動 GPT-SoVITS...
%PYTHON_EXE% webui.py

pause
