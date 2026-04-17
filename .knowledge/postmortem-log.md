# 專案踩坑紀錄（Postmortem Log）

> 記錄本專案獨有的踩坑經驗。跨專案通用的請記錄在 `postmortem-common.md`。

---

### 2026-04-17 — GPT-SoVITS WebUI 啟動時 starlette 模組缺失

| 項目 | 內容 |
|------|------|
| 分類 | runtime |
| 問題 | 執行 `scripts\04_launch_training.bat` 時，`python webui.py` 啟動失敗並拋出 `ModuleNotFoundError: No module named 'starlette._exception_handler'`，WebUI 無法進入。 |
| 原因 | `FastAPI` 會去 `from starlette._exception_handler import ...`，但環境中的 `starlette` 版本太舊（< 0.27），沒有這個模組；反之升太新（>= 0.28）又會讓 GPT-SoVITS 搭配的舊版 Gradio `TemplateResponse` 失效。兩端夾擊下，**唯一相容點是 `starlette==0.27.0`**。觸發這個錯誤的根因有兩種：（1）使用者的 bat 是舊版，沒有自動修復邏輯；（2）環境中 `starlette` 被其他套件帶走降版。 |
| 解法 | 1) 立即修復：`C:\py310\python.exe -m pip install starlette==0.27.0`。<br>2) 新增 `setup/fix_dependencies.bat` 自動鎖定 starlette 0.27.0。<br>3) `scripts/04_launch_training.bat`（main 版本）已內建啟動前檢查，若不是 0.27.0 會自動安裝。<br>4) 使用者若遇到此錯，先 `git pull` 拿最新 bat 再執行即可。 |
| 預防 | 任何由 Git 來源直接 `pip install -r` 的第三方專案（GPT-SoVITS、RVC 等）都是版本未鎖定的上游，又通常混用 FastAPI + 舊 Gradio。這類組合的正確做法不是「升版」而是「鎖版」— 找出唯一兩邊都能用的點（本專案即 starlette 0.27.0），並在啟動腳本加自動檢查，避免環境漂移。 |
| 狀態 | resolved |
| 到期日 | 2026-05-01 |
