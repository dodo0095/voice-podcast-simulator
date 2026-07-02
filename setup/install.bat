@echo off
chcp 65001 > nul
cd /d "%~dp0\.."

echo ========================================
echo  Voice Clone Project Install
echo ========================================
echo.

python --version
if errorlevel 1 (
  echo Python not found. Please install Python 3.10 for GPT-SoVITS.
  pause
  exit /b 1
)

echo.
echo [1/3] Installing project preprocessing dependencies...
python -m pip install -r setup\requirements-preprocess.txt
if errorlevel 1 (
  echo Failed to install preprocessing dependencies.
  pause
  exit /b 1
)

echo.
echo [2/3] Cloning GPT-SoVITS if missing...
if not exist "GPT-SoVITS" (
  git clone https://github.com/RVC-Boss/GPT-SoVITS.git
  if errorlevel 1 (
    echo Failed to clone GPT-SoVITS.
    pause
    exit /b 1
  )
) else (
  echo GPT-SoVITS already exists.
)

echo.
echo [3/3] Installing GPT-SoVITS dependencies...
cd GPT-SoVITS
python -m pip install -r requirements.txt
cd ..

echo.
echo Install finished. Run:
echo   python scripts\00_doctor.py
echo.
pause
