@echo off
chcp 65001 > nul
cd /d "%~dp0\.."

if not exist "GPT-SoVITS\webui.py" (
  echo Missing GPT-SoVITS. Run setup\install.bat first.
  pause
  exit /b 1
)

echo Opening GPT-SoVITS WebUI.
echo Dataset list: %CD%\data\transcripts\dataset_validated.txt
echo Wav folder:   %CD%\data\sliced
echo Experiment:   my_voice
echo.
echo Use this when CLI training does not match your GPT-SoVITS version.
pause

cd GPT-SoVITS
python webui.py
pause
