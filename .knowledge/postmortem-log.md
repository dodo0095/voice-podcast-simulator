# 專案踩坑紀錄（Postmortem Log）

> 記錄本專案獨有的踩坑經驗。跨專案通用的請記錄在 `postmortem-common.md`。

---

### 2026-04-17 — GPT-SoVITS WebUI 啟動時 starlette._exception_handler 缺失

| 項目 | 內容 |
|------|------|
| 分類 | runtime |
| 問題 | 執行 `scripts\04_launch_training.bat` 時，`python webui.py` 啟動失敗並拋出 `ModuleNotFoundError: No module named 'starlette._exception_handler'`，WebUI 無法進入。 |
| 原因 | `FastAPI` 會 `from starlette._exception_handler import ...`，但環境中 `starlette` 版本低於 FastAPI 的要求，沒這個模組。本次環境實測版本為：`fastapi==0.136.0`（要 `starlette>=0.46.0`）、`gradio==6.12.0`（要 `starlette>=0.40.0,<2.0`），所以交集是 **`starlette>=0.46.0,<2.0`**。早期 commit 裡把 starlette 鎖在 `==0.27.0` 是針對更舊版 GPT-SoVITS / 舊 Gradio 的組合，已不適用當前環境。 |
| 解法 | 1) 立即修復：`C:\py310\python.exe -m pip install "starlette>=0.46.0,<2.0"`。<br>2) `setup/fix_dependencies.bat` 改為升級策略（不寫死版本，只限制區間）。<br>3) `scripts/04_launch_training.bat` 的自動修復邏輯改為「偵測 `_exception_handler` 是否可匯入，缺了才升級到 `>=0.46.0,<2.0`」，避免無條件降版打爆新版 gradio。 |
| 預防 | **環境相依修復不能寫死版本**。GPT-SoVITS 是 git clone 上游，`gradio` 又會隨時間跳大版本（3.x → 4.x → 5.x → 6.x），不同時間點 clone 下來的環境對 starlette 的要求區間完全不同。正確做法是：以「能否匯入目標模組」作為判定條件，缺了才升級到當下兩邊都能接受的區間。把版本鎖死在歷史某個點 = 把自己困在過去。 |
| 狀態 | resolved |
| 到期日 | 2026-05-01 |
