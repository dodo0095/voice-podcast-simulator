# 🎙️ Voice Podcast Simulator

> 用自己的聲音，生成 AI Podcast 語音。  
> 基於 [GPT-SoVITS](https://github.com/RVC-Boss/GPT-SoVITS) 打造的一鍵式聲音克隆工作流程。

---

## ✨ 專案簡介

只需準備 **1 小時以上的自己聲音錄音**，本專案可以：

1. 自動切段、轉錄、校稿訓練資料
2. 訓練專屬於你聲音的 AI 模型
3. 輸入任意文字 → 生成你的聲音朗讀音訊

適合 Podcast 創作者、有聲書製作、語音內容自動化。

---

## 🖥️ 環境需求

| 項目 | 需求 |
|------|------|
| OS | Windows 10 / 11 |
| Python | 3.10（建議用 Conda） |
| GPU | NVIDIA（VRAM ≥ 8GB 建議） |
| CUDA | 11.8 或 12.1 |
| 硬碟空間 | ≥ 20GB |
| 記憶體 | ≥ 16GB |

---

## 🚀 快速開始

### 1. 安裝依賴

```bat
setup\install.bat
```

> ⏱ 首次安裝約 10~30 分鐘（含下載 GPT-SoVITS 約 2GB）

---

### 2. 準備素材

```
data/
├── raw/          ← 把你的 MP3 全部放這裡（建議 ≥ 1 小時）
└── reference/    ← 準備一段 ref.wav（3~10 秒純人聲）
```

---

### 3. 資料前處理

```bash
# Step 1：音訊切段（MP3 → WAV，依靜音自動分割）
python scripts/01_preprocess.py

# Step 2：自動轉錄（Whisper large-v3，首次會下載約 3GB）
python scripts/02_transcribe.py

# Step 3：人工校稿（抽查確認轉錄品質）
python scripts/03_validate_dataset.py
```

---

### 4. 訓練模型

```bat
scripts\04_launch_training.bat
```

瀏覽器開啟 GPT-SoVITS WebUI，依序訓練 SoVITS + GPT 模型（約 1~4 小時）。

訓練完成後，將模型複製至：

```
models/
├── sovits_model.pth
└── gpt_model.ckpt
```

---

### 5. 生成語音

**方式 A：Web UI（推薦）**

```bat
infer\start_ui.bat
```

開啟 http://localhost:7860，輸入文字即可生成。

**方式 B：CLI**

```bash
# 單段生成
python infer/infer_cli.py --text "大家好，歡迎收聽今天的節目"

# 調整語速
python infer/infer_cli.py --text "你好" --speed 0.9

# 批次生成（每行一段）
python infer/infer_cli.py --file podcast_script.txt
```

輸出音訊儲存於 `output/` 資料夾。

---

## 📁 目錄結構

```
voice/
├── configs/
│   └── voice_config.yaml       ← 主設定檔（模型路徑、訓練/推論參數）
├── data/
│   ├── raw/                    ← 原始 MP3（不進 Git）
│   ├── sliced/                 ← 切段 WAV（自動產生）
│   ├── transcripts/            ← 轉錄清單（自動產生）
│   └── reference/              ← 參考音訊 ref.wav
├── models/                     ← 訓練好的模型（不進 Git）
├── output/                     ← 生成音訊（不進 Git）
├── scripts/
│   ├── 01_preprocess.py        ← 音訊前處理
│   ├── 02_transcribe.py        ← Whisper 自動轉錄
│   ├── 03_validate_dataset.py  ← 校稿工具
│   └── 04_launch_training.bat  ← 啟動 GPT-SoVITS WebUI
├── infer/
│   ├── infer_cli.py            ← CLI 推論
│   ├── infer_ui.py             ← Web UI 推論
│   └── start_ui.bat            ← 一鍵啟動 UI
├── setup/
│   └── install.bat             ← 一鍵安裝
└── QUICK_START.md              ← 詳細操作指南
```

---

## ⚙️ 設定說明

主要設定集中在 `configs/voice_config.yaml`：

```yaml
inference:
  sovits_model_path: "models/sovits_model.pth"
  gpt_model_path: "models/gpt_model.ckpt"
  reference_audio: "data/reference/ref.wav"
  reference_text: "這裡填參考音訊說的話"
  speed_factor: 1.0   # 語速（0.8 慢 / 1.0 正常 / 1.2 快）

transcribe:
  model_size: "large-v3"   # 轉錄品質（large-v3 最準）
  device: "cuda"
```

---

## 📊 效能參考

| GPU | 生成 100 字 | 訓練時間（2h 資料） |
|-----|------------|------------------|
| RTX 3060 12GB | ~5 秒 | ~2 小時 |
| RTX 3090 24GB | ~3 秒 | ~1 小時 |
| RTX 4090 24GB | ~2 秒 | ~40 分鐘 |

---

## ❓ 常見問題

**Q: CUDA 記憶體不足（OOM）？**  
→ 在 `voice_config.yaml` 將 `batch_size` 從 4 改為 2

**Q: 轉錄很慢？**  
→ 將 `model_size` 改為 `medium`，`compute_type` 改為 `int8`

**Q: 聲音不夠像我？**  
→ 確保訓練資料 ≥ 1 小時；嘗試不同的參考音訊；增加訓練 Epoch

**Q: 生成有雜音或斷音？**  
→ 調整推論參數 `top_k: 3`、`temperature: 0.8`；或更換參考音訊

---

## 📦 套件管理

本專案使用 [uv](https://github.com/astral-sh/uv) 管理 Python 依賴：

```bash
# 安裝套件（禁止直接使用 pip install）
uv add <package>

# 同步所有依賴
uv sync
```

---

## 📄 授權

本專案依賴 [GPT-SoVITS](https://github.com/RVC-Boss/GPT-SoVITS)，請遵守其授權條款。
