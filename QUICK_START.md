# Quick Start

最短流程：

```bat
setup\install.bat
python scripts\00_doctor.py
```

把錄音放進：

```text
data/raw/
```

然後依序執行：

```bat
python scripts\01_preprocess.py --clean
python scripts\02_transcribe.py
python scripts\03_validate_dataset.py
python scripts\05_make_reference.py
scripts\04_train_cli.bat
python infer\infer_cli.py --text "這是一段測試語音。"
```

如果 CLI 訓練失敗，通常是 GPT-SoVITS 版本差異，改用：

```bat
scripts\04_launch_training.bat
```

WebUI 裡填：

```text
dataset: data/transcripts/dataset_validated.txt
wav dir: data/sliced
experiment: my_voice
```

常見問題：

- Python 3.13：資料整理可跑，但 GPT-SoVITS 建議 Python 3.10。
- CUDA OOM：把 `configs/voice_config.yaml` 的 `training.batch_size` 改成 2。
- 聲音不像：先檢查 dataset 文字是否正確，再增加乾淨單人聲資料。
- 發音怪：reference text 必須和 `data/reference/ref.wav` 內容完全一致。
