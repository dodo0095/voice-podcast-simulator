# 專案踩坑紀錄（Postmortem Log）

> 記錄本專案獨有的踩坑經驗。跨專案通用的請記錄在 `postmortem-common.md`。

---

### 2026-04-17 — GPT-SoVITS WebUI 啟動時 starlette 模組缺失

| 項目 | 內容 |
|------|------|
| 分類 | runtime |
| 問題 | 執行 `scripts\04_launch_training.bat` 時，`python webui.py` 啟動失敗並拋出 `ModuleNotFoundError: No module named 'starlette._exception_handler'`，WebUI 無法進入。 |
| 原因 | GPT-SoVITS 原始 `requirements.txt` 指定的 `fastapi` 與 `starlette` 是較舊版；`setup/install.bat` 在步驟 4 又執行 `pip install gradio>=4.0.0`，gradio 4.44+ 會把 `fastapi` 升級到 0.110+，但 `starlette` 未一同升級。新版 `fastapi` 需要 `starlette>=0.36`（才有 `_exception_handler` 子模組），於是發生交錯版本衝突。 |
| 解法 | 1) 立即修復：`C:\py310\python.exe -m pip install --upgrade "fastapi>=0.110.0" "starlette>=0.36.3" "gradio>=4.44.0"`。<br>2) 新增 `setup/fix_dependencies.bat` 一鍵修復腳本。<br>3) `setup/install.bat` 步驟 4 改成同時鎖定 fastapi / starlette / gradio 的最低版本，避免下次重裝再踩。<br>4) `scripts/04_launch_training.bat` 在 `python webui.py` 失敗時主動提示執行 `fix_dependencies.bat`。 |
| 預防 | 任何由 Git 來源直接 `pip install -r` 的第三方專案（例如 GPT-SoVITS）都要視為「版本未鎖定的上游」。之後再裝與其共用 FastAPI/Starlette 生態系的套件（gradio、uvicorn、starlette-admin…）時，必須在 install 腳本裡**同時**指定這些套件的最低相容版本，避免隱性升級產生的版本交錯。|
| 狀態 | resolved |
| 到期日 | 2026-05-01 |
