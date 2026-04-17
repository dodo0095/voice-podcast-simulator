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

:: 修復 Starlette 版本相容問題
:: 需要 ==0.27.0：>= 0.27 讓 FastAPI 找到 _exception_handler，< 0.28 讓舊 Gradio TemplateResponse 正常運作
echo 檢查 Starlette 版本...
%PYTHON_EXE% -c "import starlette; exit(0 if starlette.__version__ == '0.27.0' else 1)" 2>nul
if errorlevel 1 (
    echo [修復] 安裝 Starlette 0.27.0（FastAPI + Gradio 相容版本）...
    %PYTHON_EXE% -m pip install "starlette==0.27.0" --quiet
    echo [完成] Starlette 已修復
) else (
    echo [OK] Starlette 版本相容 ^(0.27.0^)
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
