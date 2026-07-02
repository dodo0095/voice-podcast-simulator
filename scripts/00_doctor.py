#!/usr/bin/env python3
"""Check the local environment and project state."""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

import yaml
from colorama import Fore, Style, init

init()

ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT / "configs" / "voice_config.yaml"


def ok(message: str) -> None:
    print(f"{Fore.GREEN}[OK]{Style.RESET_ALL} {message}")


def warn(message: str) -> None:
    print(f"{Fore.YELLOW}[WARN]{Style.RESET_ALL} {message}")


def fail(message: str) -> None:
    print(f"{Fore.RED}[FAIL]{Style.RESET_ALL} {message}")


def load_config() -> dict:
    with open(CONFIG_PATH, encoding="utf-8") as f:
        return yaml.safe_load(f)


def count_files(path: Path, pattern: str) -> int:
    return len(list(path.glob(pattern))) if path.exists() else 0


def raw_audio_count(raw_dir: Path) -> int:
    extensions = ["mp3", "wav", "m4a", "flac", "ogg", "aac"]
    return sum(count_files(raw_dir, f"*.{ext}") for ext in extensions)


def check_torch_cuda() -> None:
    code = (
        "import torch; "
        "print(torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'NO_CUDA')"
    )
    try:
        result = subprocess.run(
            [sys.executable, "-c", code],
            text=True,
            capture_output=True,
            timeout=8,
            check=False,
        )
    except subprocess.TimeoutExpired:
        warn("torch CUDA check timed out")
        return
    except Exception:
        warn("torch not installed in this environment")
        return

    if result.returncode != 0:
        warn("torch not installed or failed to import")
        return
    device = result.stdout.strip()
    if device and device != "NO_CUDA":
        ok(f"CUDA available: {device}")
    else:
        warn("torch installed but CUDA is not available")


def main() -> None:
    config = load_config()
    paths = config["paths"]

    print("\nVoice project doctor\n")

    version = sys.version_info
    if version.major == 3 and version.minor == 10:
        ok(f"Python {version.major}.{version.minor}.{version.micro}")
    else:
        warn(f"目前 Python 是 {version.major}.{version.minor}.{version.micro}；GPT-SoVITS 建議 Python 3.10。")

    if shutil.which("ffmpeg"):
        ok("ffmpeg found")
    else:
        fail("ffmpeg not found in PATH")

    check_torch_cuda()

    for key in ["raw_dir", "sliced_dir", "transcript_dir", "reference_dir", "output_dir", "models_dir"]:
        path = ROOT / paths[key]
        if path.exists():
            ok(f"{key}: {path}")
        else:
            warn(f"{key} missing: {path}")

    raw_dir = ROOT / paths["raw_dir"]
    sliced_dir = ROOT / paths["sliced_dir"]
    transcript_dir = ROOT / paths["transcript_dir"]
    reference_dir = ROOT / paths["reference_dir"]
    models_dir = ROOT / paths["models_dir"]
    gptsovits_dir = ROOT / paths["gptsovits_dir"]

    print("\nProject data")
    print(f"raw audio: {raw_audio_count(raw_dir)}")
    print(f"sliced wav: {count_files(sliced_dir, '*.wav')}")
    print(f"dataset_list: {(transcript_dir / 'dataset_list.txt').exists()}")
    print(f"dataset_validated: {(transcript_dir / 'dataset_validated.txt').exists()}")
    print(f"reference wav: {count_files(reference_dir, '*.wav')}")
    print(f"models: {count_files(models_dir, '*.pth')} pth, {count_files(models_dir, '*.ckpt')} ckpt")

    if gptsovits_dir.exists():
        ok(f"GPT-SoVITS directory exists: {gptsovits_dir}")
    else:
        warn(f"GPT-SoVITS missing: {gptsovits_dir}")

    print("\nSuggested next command")
    if raw_audio_count(raw_dir) == 0:
        print("Put your recordings into data/raw")
    elif count_files(sliced_dir, "*.wav") == 0:
        print("python scripts/01_preprocess.py --clean")
    elif not (transcript_dir / "dataset_list.txt").exists():
        print("python scripts/02_transcribe.py")
    elif not (transcript_dir / "dataset_validated.txt").exists():
        print("python scripts/03_validate_dataset.py")
    elif not (ROOT / config["inference"]["reference_audio"]).exists():
        print("python scripts/05_make_reference.py")
    elif count_files(models_dir, "*.pth") == 0 or count_files(models_dir, "*.ckpt") == 0:
        print("scripts\\04_train_cli.bat")
    else:
        print("python infer/infer_cli.py --text \"測試一句話\"")


if __name__ == "__main__":
    main()
