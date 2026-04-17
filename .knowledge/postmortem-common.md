# 跨專案通用踩坑紀錄

> 由 /knowledge-feedback Skill 自動維護，記錄跨專案通用的踩坑經驗。
> **版本**: v1.0
> **最後更新**: 2026-03-26

---

## 通用踩坑紀錄

| 日期 | 來源專案 | 分類 | 問題摘要 | 解法 | 相關規範 |
|------|---------|------|---------|------|---------|
| 2026-04-17 | voice | 環境 / 相依套件 | `python webui.py` 啟動報 `ModuleNotFoundError: No module named 'starlette._exception_handler'`，原因為 GPT-SoVITS `requirements.txt` 釘較舊的 fastapi/starlette，之後 `pip install gradio` 拉新版 fastapi，導致版本交錯。 | 執行 `setup\fix_dependencies.bat`，或 `pip install --upgrade "fastapi>=0.110.0" "starlette>=0.36.3" "gradio>=4.44.0"`；install.bat 已固定最低版本 | coding-standards.md（依賴/環境變數規則） |

> 當此表有新增紀錄時，建議同步檢查對應的公司規範文件是否需要更新。
