# 🎙️ AI 聲音克隆 — 快速上手指南

## 一、環境需求（GPU 電腦）

| 項目 | 需求 |
|------|------|
| OS | Windows 10/11 |
| Python | 3.10（建議用 Conda 管理） |
| GPU | NVIDIA（VRAM ≥ 8GB 建議） |
| CUDA | 11.8 或 12.1 |
| 硬碟空間 | ≥ 20GB（模型 + 資料） |
| 記憶體 | ≥ 16GB |

---

## 二、第一次執行（完整流程）

### 【準備工作】放好素材

```
voice/
└── data/
    └── raw/          ← 把你的 MP3 全部丟這裡
    └── reference/    ← 準備一段 ref.wav（3~10秒純人聲）
```

---

### 【Step 0】一鍵安裝

```bat
setup\install.bat
```

這會自動：
- 安裝所有 Python 套件
- 下載 GPT-SoVITS（約 2GB）

⏱ 首次約需 10~30 分鐘（依網速）

---

### 【Step 1】音訊前處理

```bash
python scripts/01_preprocess.py
```

**做了什麼：**
- 把 MP3 轉成 WAV（16kHz 單聲道）
- 依靜音自動切段（3~10秒/段）
- 正規化音量

**完成後看到：**
```
data/sliced/    ← 幾百個 WAV 切段
```

---

### 【Step 2】自動語音轉錄

```bash
python scripts/02_transcribe.py
```

**做了什麼：**
- 用 Whisper large-v3 自動轉錄每段音訊
- 輸出訓練清單（音訊路徑 + 對應文字）

⚠️ **首次會下載 Whisper 模型（約 3GB）**，請耐心等候

**完成後看到：**
```
data/transcripts/dataset_list.txt    ← 訓練清單
```

---

### 【Step 3】人工校稿（重要！）

```bash
# 一般模式（互動校稿）
python scripts/03_validate_dataset.py

# 快速模式（跳過校稿，全部保留）
python scripts/03_validate_dataset.py --skip
```

**做了什麼：**
- 顯示每段的轉錄文字
- 讓你確認/修正/刪除

**操作按鍵（一般模式）：**
| 按鍵 | 動作 |
|------|------|
| Enter | 保留（轉錄正確） |
| e | 編輯文字 |
| d | 刪除此段 |
| p | 播放音訊 |
| s | 儲存並離開 |

> 💡 不需要校稿 100%，抽查幾十筆、刪掉明顯錯誤的就夠了
> 💡 `--skip` 模式會把全部資料直接寫入 `dataset_validated.txt`，適合快速測試流程

**完成後看到：**
```
data/transcripts/dataset_validated.txt    ← 乾淨的訓練清單
```

---

### 【Step 4】訓練模型

```bat
scripts\04_launch_training.bat
```

這會開啟 **GPT-SoVITS WebUI**，在瀏覽器中操作：

#### 4-1. 訓練 SoVITS 模型

1. 點擊「**SoVITS 訓練**」分頁
2. 「訓練列表路徑」填入：
   ```
   data\transcripts\dataset_validated.txt  的完整路徑
   ```
3. 「實驗名稱」填：`my_voice`
4. Batch Size：4（VRAM < 8GB 改為 2）
5. Epoch：`8`（資料多可設 16）
6. 點擊「**一鍵三連**」→ 等待完成

#### 4-2. 訓練 GPT 模型

1. 切到「**GPT 訓練**」分頁
2. 同樣填訓練列表路徑
3. Epoch：`15`
4. 點擊開始訓練

⏱ 訓練時間：依資料量和 GPU 而定，約 1~4 小時

---

### 【Step 5】設定模型路徑

訓練完成後：

1. 找到模型檔案（通常在 `GPT-SoVITS/logs/my_voice/`）：
   - `*.pth` → SoVITS 模型
   - `*.ckpt` → GPT 模型

2. 複製到 `models/` 資料夾，改名：
   ```
   models/
   ├── sovits_model.pth
   └── gpt_model.ckpt
   ```

3. 準備參考音訊：
   - 從 `data/sliced/` 選一段最清晰的
   - 複製到 `data/reference/ref.wav`
   - 記住這段說的話（等等填設定）

4. 更新 `configs/voice_config.yaml`：
   ```yaml
   inference:
     sovits_model_path: "models/sovits_model.pth"
     gpt_model_path: "models/gpt_model.ckpt"
     reference_audio: "data/reference/ref.wav"
     reference_text: "這裡填參考音訊說的話"
   ```

---

### 【Step 6】開始使用！

#### 方式 A：Web UI（推薦）

```bat
infer\start_ui.bat
```
瀏覽器開啟 http://localhost:7860，輸入文案即可生成

#### 方式 B：CLI 指令

```bash
# 單段生成
python infer/infer_cli.py --text "大家好，歡迎收聽今天的節目"

# 指定語速
python infer/infer_cli.py --text "你好" --speed 0.9

# 批次生成（一個文字檔，每行一條）
python infer/infer_cli.py --file podcast_script.txt
```

輸出檔案在 `output/` 資料夾

---

## 三、目錄結構說明

```
voice/
├── QUICK_START.md          ← 本文件
├── configs/
│   └── voice_config.yaml   ← 主設定檔
├── data/
│   ├── raw/                ← 放原始 MP3
│   ├── sliced/             ← 自動切段（Step 1 產生）
│   ├── transcripts/        ← 轉錄結果（Step 2 產生）
│   └── reference/          ← 參考音訊 ref.wav
├── models/                 ← 放訓練好的模型
├── output/                 ← 生成的音訊輸出
├── scripts/
│   ├── 01_preprocess.py    ← 音訊前處理
│   ├── 02_transcribe.py    ← 自動轉錄
│   ├── 03_validate_dataset.py ← 校稿工具
│   └── 04_launch_training.bat ← 啟動訓練
├── infer/
│   ├── infer_cli.py        ← CLI 推論
│   ├── infer_ui.py         ← Web UI 推論
│   └── start_ui.bat        ← 一鍵啟動 UI
├── setup/
│   ├── install.bat         ← 一鍵安裝
│   └── requirements-preprocess.txt
└── GPT-SoVITS/             ← 安裝後自動產生
```

---

## 四、常見問題

### Q: CUDA 記憶體不足（OOM）？
```yaml
# 在 voice_config.yaml 降低 batch_size
training:
  batch_size: 2  # 從 4 改為 2
```

### Q: 轉錄跑很慢？
改用較小的 Whisper 模型：
```yaml
transcribe:
  model_size: "medium"   # 從 large-v3 改為 medium
  compute_type: "int8"   # 用 INT8 加速
```

### Q: 生成的聲音不夠像我？
1. 確認訓練資料 **時長夠長**（≥ 1 小時）
2. 嘗試不同的**參考音訊**（對生成品質影響很大）
3. 填寫**參考音訊內容**（ref_text）
4. 增加訓練 Epoch 數

### Q: 生成結果有雜音/斷音？
- 調整推論參數：`top_k: 3`, `temperature: 0.8`
- 更換參考音訊

### Q: 如何更新模型（重新訓練）？
重複 Step 4，覆蓋 `models/` 裡的檔案即可

---

## 五、效能參考

| GPU | 生成 100 字 | 訓練時間（2h 資料） |
|-----|------------|-----------------|
| RTX 3060 12GB | ~5 秒 | ~2 小時 |
| RTX 3090 24GB | ~3 秒 | ~1 小時 |
| RTX 4090 24GB | ~2 秒 | ~40 分鐘 |

---

有任何問題回報給 PM 即可 🎙️
