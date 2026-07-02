# Project Notes

This is a local voice cloning workflow built around GPT-SoVITS.

Use `uv` or `pip` consistently inside the active Python environment. GPT-SoVITS is most reliable with Python 3.10.

Primary commands:

```bat
python scripts\00_doctor.py
python scripts\01_preprocess.py --clean
python scripts\02_transcribe.py
python scripts\03_validate_dataset.py
python scripts\05_make_reference.py
scripts\04_train_cli.bat
python infer\infer_cli.py --text "測試一句話"
```

Do not commit raw audio, generated slices, trained models, or output audio.
