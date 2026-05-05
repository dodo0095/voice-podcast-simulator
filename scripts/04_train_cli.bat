@echo off
chcp 65001 > nul
echo ========================================
echo  Step 4 (CLI版): GPT-SoVITS 命令列訓練
echo  不需要 WebUI，全自動執行
echo ========================================
echo.

cd /d "%~dp0\.."
set PROJECT_ROOT=%CD%
set DATASET_LIST=%PROJECT_ROOT%\data\transcripts\dataset_validated.txt
set SLICED_DIR=%PROJECT_ROOT%\data\sliced
set EXP_NAME=my_voice

:: ── 偵測 Python ──────────────────────────────────────────
set PYTHON_EXE=
if exist "C:\py310\python.exe" (
    set PYTHON_EXE=C:\py310\python.exe
    echo [OK] 使用 C:\py310\python.exe
    goto :python_found
)
where python >nul 2>&1
if not errorlevel 1 (
    set PYTHON_EXE=python
    echo [OK] 使用系統 Python
    goto :python_found
)
echo [錯誤] 找不到 Python
pause & exit /b 1
:python_found

:: ── 前置檢查：訓練資料 ───────────────────────────────────
if not exist "%DATASET_LIST%" (
    echo.
    echo [錯誤] 找不到訓練清單:
    echo   %DATASET_LIST%
    echo.
    echo 請先執行: python scripts\03_validate_dataset.py
    pause & exit /b 1
)
for /f %%c in ('find /c /v "" "%DATASET_LIST%"') do set LINE_COUNT=%%c
echo [OK] 訓練資料: %LINE_COUNT% 筆

:: ── 尋找 GPT-SoVITS 資料夾 ───────────────────────────────
set GPTSOVITS_DIR=

:: 優先：專案內
if exist "%PROJECT_ROOT%\GPT-SoVITS\GPT_SoVITS\s2_train.py" (
    set GPTSOVITS_DIR=%PROJECT_ROOT%\GPT-SoVITS
    echo [OK] GPT-SoVITS 位置: %GPTSOVITS_DIR%
    goto :gptsovits_found
)

:: 次選：桌面
if exist "%USERPROFILE%\Desktop\GPT-SoVITS\GPT_SoVITS\s2_train.py" (
    set GPTSOVITS_DIR=%USERPROFILE%\Desktop\GPT-SoVITS
    echo [OK] GPT-SoVITS 位置: %GPTSOVITS_DIR%
    goto :gptsovits_found
)

:: 三選：C 槽根目錄
if exist "C:\GPT-SoVITS\GPT_SoVITS\s2_train.py" (
    set GPTSOVITS_DIR=C:\GPT-SoVITS
    echo [OK] GPT-SoVITS 位置: %GPTSOVITS_DIR%
    goto :gptsovits_found
)

:: 四選：D 槽
if exist "D:\GPT-SoVITS\GPT_SoVITS\s2_train.py" (
    set GPTSOVITS_DIR=D:\GPT-SoVITS
    echo [OK] GPT-SoVITS 位置: %GPTSOVITS_DIR%
    goto :gptsovits_found
)

:: 找不到，讓使用者手動指定
echo.
echo [提示] 自動偵測失敗，找不到 GPT-SoVITS
echo.
echo 請問你的 GPT-SoVITS 安裝在哪裡？
echo （就是包含 webui.py 的那個資料夾）
echo.
set /p GPTSOVITS_DIR=請輸入完整路徑:

if not exist "%GPTSOVITS_DIR%\GPT_SoVITS\s2_train.py" (
    echo.
    echo [錯誤] 指定路徑找不到 GPT-SoVITS 核心檔案
    echo 預期位置: %GPTSOVITS_DIR%\GPT_SoVITS\s2_train.py
    echo.
    echo 如果你還沒安裝 GPT-SoVITS，請先執行: setup\install.bat
    pause & exit /b 1
)

:gptsovits_found
echo.
echo ========================================
echo  設定確認
echo ========================================
echo   實驗名稱 : %EXP_NAME%
echo   訓練資料 : %DATASET_LIST%
echo   音訊資料夾: %SLICED_DIR%
echo   GPT-SoVITS: %GPTSOVITS_DIR%
echo.
echo 即將開始訓練（約 1~4 小時）
echo 此視窗請勿關閉！
echo.
pause

:: ── 執行 Python 訓練腳本 ─────────────────────────────────
%PYTHON_EXE% "%PROJECT_ROOT%\scripts\04_train_cli.py" ^
    --dataset "%DATASET_LIST%" ^
    --wav_dir "%SLICED_DIR%" ^
    --exp_name "%EXP_NAME%" ^
    --gptsovits_dir "%GPTSOVITS_DIR%"

if errorlevel 1 (
    echo.
    echo ========================================
    echo  [失敗] 訓練過程發生錯誤
    echo ========================================
    echo.
    echo 常見解法：
    echo   1. VRAM 不足 → 修改 voice_config.yaml 把 batch_size 改為 2
    echo   2. 缺少套件  → 執行 pip install -r GPT-SoVITS\requirements.txt
    echo   3. 路徑問題  → 確認 data\transcripts\dataset_validated.txt 存在
    echo.
    pause & exit /b 1
)

echo.
echo ========================================
echo  訓練完成！
echo ========================================
echo.
echo 模型已存放在:
echo   %PROJECT_ROOT%\models\sovits_model.pth
echo   %PROJECT_ROOT%\models\gpt_model.ckpt
echo.
echo 下一步: 執行 infer\start_ui.bat 開始使用！
echo.
pause
