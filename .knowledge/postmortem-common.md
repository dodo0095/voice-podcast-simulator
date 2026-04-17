# 跨專案通用踩坑紀錄

> 由 /knowledge-feedback Skill 自動維護，記錄跨專案通用的踩坑經驗。
> **版本**: v1.0
> **最後更新**: 2026-03-26

---

## 通用踩坑紀錄

| 日期 | 來源專案 | 分類 | 問題摘要 | 解法 | 相關規範 |
|------|---------|------|---------|------|---------|
| 2026-04-17 | voice | 環境 / 相依套件 | `python webui.py` 啟動報 `ModuleNotFoundError: No module named 'starlette._exception_handler'`。原因：FastAPI 需要 starlette >= 0.27，但舊 Gradio 的 TemplateResponse 又不相容 >= 0.28，唯一相容點是 `starlette==0.27.0`。 | 執行 `setup\fix_dependencies.bat`，或 `pip install starlette==0.27.0`。啟動腳本 `04_launch_training.bat` 已內建自動檢查與修復。 | coding-standards.md（依賴/環境變數規則） |

> 當此表有新增紀錄時，建議同步檢查對應的公司規範文件是否需要更新。
