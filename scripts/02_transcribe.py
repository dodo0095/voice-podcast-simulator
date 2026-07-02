#!/usr/bin/env python3
"""Transcribe prepared voice segments with faster-whisper."""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

import yaml
from colorama import Fore, Style, init
from tqdm import tqdm

init()

ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT / "configs" / "voice_config.yaml"


def load_config() -> dict:
    with open(CONFIG_PATH, encoding="utf-8") as f:
        return yaml.safe_load(f)


def rel_path(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def load_model(cfg: dict):
    try:
        from faster_whisper import WhisperModel
    except ImportError as exc:
        raise SystemExit("缺少 faster-whisper，請先執行 setup\\install.bat 或 pip install faster-whisper。") from exc

    print(f"載入 Whisper：{cfg['model_size']} ({cfg['device']}, {cfg['compute_type']})")
    try:
        return WhisperModel(
            cfg["model_size"],
            device=cfg["device"],
            compute_type=cfg["compute_type"],
        )
    except Exception:
        if cfg["device"] == "cuda":
            print(f"{Fore.YELLOW}CUDA 載入失敗，改用 CPU/int8。{Style.RESET_ALL}")
            return WhisperModel(cfg["model_size"], device="cpu", compute_type="int8")
        raise


def transcribe_one(model, wav_path: Path, cfg: dict, asr_language: str) -> tuple[str, float | None]:
    segments, _info = model.transcribe(
        str(wav_path),
        language=asr_language,
        beam_size=int(cfg["beam_size"]),
        vad_filter=bool(cfg["vad_filter"]),
        vad_parameters={"min_silence_duration_ms": 500},
    )

    texts: list[str] = []
    scores: list[float] = []
    threshold = float(cfg["confidence_threshold"])

    for seg in segments:
        text = seg.text.strip()
        if not text:
            continue
        score = float(seg.avg_logprob)
        if score < threshold:
            continue
        texts.append(text)
        scores.append(score)

    text = "".join(texts).strip()
    avg_score = sum(scores) / len(scores) if scores else None
    return text, avg_score


def existing_audio_names(dataset_path: Path) -> set[str]:
    names: set[str] = set()
    if not dataset_path.exists():
        return names
    with open(dataset_path, encoding="utf-8") as f:
        for line in f:
            parts = line.rstrip("\n").split("|", 3)
            if len(parts) == 4:
                names.add(Path(parts[0]).name)
    return names


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Transcribe data/sliced wav files.")
    parser.add_argument("--overwrite", action="store_true", help="Recreate transcript files from scratch.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config = load_config()
    paths = config["paths"]
    cfg = config["transcribe"]
    speaker = config["speaker"]["name"]
    lang = config["speaker"]["language"]
    asr_language = config["speaker"]["asr_language"]

    sliced_dir = ROOT / paths["sliced_dir"]
    transcript_dir = ROOT / paths["transcript_dir"]
    transcript_dir.mkdir(parents=True, exist_ok=True)
    dataset_path = transcript_dir / "dataset_list.txt"
    csv_path = transcript_dir / "transcripts.csv"
    failed_path = transcript_dir / "failed.txt"

    print(f"\n{Fore.CYAN}Step 2: transcribe segments{Style.RESET_ALL}")

    wav_files = sorted(sliced_dir.glob("*.wav"))
    if not wav_files:
        raise SystemExit("data/sliced 沒有 wav，請先執行 python scripts/01_preprocess.py")

    if args.overwrite:
        for path in [dataset_path, csv_path, failed_path]:
            if path.exists():
                path.unlink()

    done = existing_audio_names(dataset_path)
    pending = [p for p in wav_files if p.name not in done]
    print(f"總段數：{len(wav_files)}，待轉錄：{len(pending)}")
    if not pending:
        print("沒有需要轉錄的新檔案。")
        return

    model = load_model(cfg)
    csv_exists = csv_path.exists()
    min_chars = int(cfg["min_text_chars"])
    success = 0
    failed = 0

    with open(dataset_path, "a", encoding="utf-8") as dataset_f, \
            open(csv_path, "a", newline="", encoding="utf-8") as csv_f, \
            open(failed_path, "a", encoding="utf-8") as failed_f:
        writer = csv.DictWriter(csv_f, fieldnames=["audio_path", "text", "avg_logprob"])
        if not csv_exists:
            writer.writeheader()

        for wav_path in tqdm(pending, desc="Transcribing", unit="clip"):
            try:
                text, avg_score = transcribe_one(model, wav_path, cfg, asr_language)
            except Exception as exc:
                failed_f.write(f"{rel_path(wav_path)}\t{exc}\n")
                failed += 1
                continue

            if len(text) < min_chars:
                failed_f.write(f"{rel_path(wav_path)}\tempty_or_too_short\n")
                failed += 1
                continue

            abs_audio = str(wav_path.resolve())
            dataset_f.write(f"{abs_audio}|{speaker}|{lang}|{text}\n")
            writer.writerow({
                "audio_path": abs_audio,
                "text": text,
                "avg_logprob": "" if avg_score is None else f"{avg_score:.4f}",
            })
            success += 1

    print(f"\n完成：成功 {success}，失敗/略過 {failed}")
    print(f"輸出：{rel_path(dataset_path)}")
    print(f"下一步：python scripts/03_validate_dataset.py")


if __name__ == "__main__":
    main()
