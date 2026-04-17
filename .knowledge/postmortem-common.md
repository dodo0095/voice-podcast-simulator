# 跨專案通用踩坑紀錄

> 由 /knowledge-feedback Skill 自動維護，記錄跨專案通用的踩坑經驗。
> **版本**: v1.0
> **最後更新**: 2026-03-26

---

## 通用踩坑紀錄

| 日期 | 來源專案 | 分類 | 問題摘要 | 解法 | 相關規範 |
|------|---------|------|---------|------|---------|
| 2026-04-17 | voice | 環境 / 相依套件 | `python webui.py` 啟動報 `ModuleNotFoundError: No module named 'starlette._exception_handler'`。FastAPI / Gradio 都隨時間跳大版本，不同時間點 clone 的環境對 starlette 的版本區間要求完全不同，**鎖死版本 = 把自己困在過去**。 | 以「能否匯入 `starlette._exception_handler`」為判定條件，缺了才升級到當前 fastapi + gradio 交集區間（本次環境為 `>=0.46.0,<2.0`）。執行 `setup\fix_dependencies.bat`。 | coding-standards.md（依賴/環境變數規則） |

> 當此表有新增紀錄時，建議同步檢查對應的公司規範文件是否需要更新。
