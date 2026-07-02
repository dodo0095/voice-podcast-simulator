@echo off
chcp 65001 > nul
cd /d "%~dp0\.."
echo Starting Voice Clone Web UI...
python infer\infer_ui.py
pause
