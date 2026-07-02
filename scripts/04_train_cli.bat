@echo off
chcp 65001 > nul
cd /d "%~dp0\.."

set PROJECT_ROOT=%CD%
set DATASET_LIST=%PROJECT_ROOT%\data\transcripts\dataset_validated.txt
set SLICED_DIR=%PROJECT_ROOT%\data\sliced
set GPTSOVITS_DIR=%PROJECT_ROOT%\GPT-SoVITS

if not exist "%DATASET_LIST%" (
  echo Missing %DATASET_LIST%
  echo Run: python scripts\03_validate_dataset.py
  pause
  exit /b 1
)

if not exist "%GPTSOVITS_DIR%" (
  echo Missing GPT-SoVITS folder.
  echo Run: setup\install.bat
  pause
  exit /b 1
)

python scripts\04_train_cli.py ^
  --dataset "%DATASET_LIST%" ^
  --wav_dir "%SLICED_DIR%" ^
  --gptsovits_dir "%GPTSOVITS_DIR%"

pause
