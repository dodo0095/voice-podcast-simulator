# Voice Clone Studio

這個專案用來把大量自己的錄音整理成可訓練資料，並接到 GPT-SoVITS 做中文聲音 clone。

核心目標不是只拿 30 秒 reference 做 zero-shot，而是把多個音檔整理成乾淨的 few-shot/fine-tune dataset，讓模型真的學到你的音色、語速和說話習慣。

## 推薦流程

1. 安裝環境

```bat
setup\install.bat
python scripts\00_doctor.py
```

GPT-SoVITS 建議 Python 3.10。你目前如果用 Python 3.13，可以跑資料整理腳本，但 GPT-SoVITS 依賴很可能不穩。

2. 放入原始錄音

把 mp3/wav/m4a/flac 放到：

```text
data/raw/
```

資料越乾淨越好：單人聲、少背景音樂、少混響、不要多人對話。

3. 切段與音量整理

```bat
python scripts\01_preprocess.py --clean
```

輸出：

```text
data/sliced/*.wav
data/transcripts/segments.csv
```

4. Whisper 自動轉錄

```bat
python scripts\02_transcribe.py
```

輸出：

```text
data/transcripts/dataset_list.txt
data/transcripts/transcripts.csv
data/transcripts/failed.txt
```

5. 人工審校

```bat
python scripts\03_validate_dataset.py
```

如果只是先快速測試：

```bat
python scripts\03_validate_dataset.py --skip
```

正式訓練建議人工聽過並修正文字。文字錯會直接傷害 TTS 品質。

6. 產生 reference clip

```bat
python scripts\05_make_reference.py
```

它會從已審校資料挑一段 5-10 秒的乾淨 reference，寫到：

```text
data/reference/ref.wav
data/reference/ref.txt
```

也可以手動指定：

```bat
python scripts\05_make_reference.py --audio path\to\clip.wav --text "這段音檔實際說的文字"
```

7. 訓練 GPT-SoVITS

優先試 CLI：

```bat
scripts\04_train_cli.bat
```

如果你的 GPT-SoVITS 版本和 CLI wrapper 不相容，改用官方 WebUI：

```bat
scripts\04_launch_training.bat
```

WebUI 內使用：

```text
dataset: data/transcripts/dataset_validated.txt
wav dir: data/sliced
experiment: my_voice
```

訓練完成後，把模型放到：

```text
models/sovits_model.pth
models/gpt_model.ckpt
```

CLI wrapper 成功時會自動複製最新模型。

8. 推論

```bat
python infer\infer_cli.py --text "歡迎收聽，史塔克實驗室！"
```

或開 Web UI：

```bat
infer\start_ui.bat
```

輸出會在：

```text
output/
```

## 資料量建議

最低可測：

- 100 段以上
- 約 10-30 分鐘乾淨人聲

比較穩：

- 300 段以上
- 30-60 分鐘乾淨人聲

更重要的是品質，不是長度。1 小時乾淨單人聲通常比 5 小時含音樂、多人插話、轉錄錯誤的資料好。

## 目前專案結構

```text
configs/voice_config.yaml       主要設定
data/raw/                       原始錄音
data/sliced/                    切好的訓練片段
data/transcripts/               Whisper 與審校輸出
data/reference/                 推論 reference
models/                         fine-tune 後模型
output/                         生成音檔
scripts/00_doctor.py            環境檢查
scripts/01_preprocess.py        切音與 normalize
scripts/02_transcribe.py        Whisper 轉錄
scripts/03_validate_dataset.py  審校文字
scripts/04_train_cli.py         GPT-SoVITS CLI 訓練 wrapper
scripts/05_make_reference.py    建立 reference clip
infer/infer_cli.py              命令列推論
infer/infer_ui.py               Gradio 推論 UI
```

## 調參位置

主要改 [configs/voice_config.yaml](configs/voice_config.yaml)：

- `preprocess.min_segment_sec` / `max_segment_sec`：切段長度
- `preprocess.silence_threshold_db`：靜音切割門檻
- `transcribe.device`：`cuda` 或 `cpu`
- `training.batch_size`：VRAM 不夠時從 4 改 2
- `inference.temperature`：越高越有變化，但越可能不穩
- `inference.speed_factor`：語速

## 重要提醒

請只 clone 你自己的聲音，或已取得明確授權的聲音。不要用這套流程冒充他人。
