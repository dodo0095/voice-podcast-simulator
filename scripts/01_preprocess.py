#!/usr/bin/env python3
"""Prepare raw voice recordings for GPT-SoVITS fine-tuning.

The script reads audio files from data/raw, converts them to mono WAV, splits
them into trainable 3-12 second clips, normalizes loudness, and writes metadata
for later auditing.
"""

from __future__ import annotations

import argparse
import csv
import logging
import shutil
import sys
from pathlib import Path

import yaml
from colorama import Fore, Style, init
from tqdm import tqdm

init()

ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT / "configs" / "voice_config.yaml"
AUDIO_EXTENSIONS = {".mp3", ".wav", ".m4a", ".aac", ".flac", ".ogg", ".wma"}

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("preprocess")


def load_config() -> dict:
    with open(CONFIG_PATH, encoding="utf-8") as f:
        return yaml.safe_load(f)


def rel_path(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def check_ffmpeg() -> None:
    if not shutil.which("ffmpeg"):
        raise SystemExit(
            "找不到 ffmpeg。請先安裝 ffmpeg，並確認 ffmpeg.exe 可以在 PATH 中執行。"
        )


def find_audio_files(raw_dir: Path) -> list[Path]:
    files = [
        p for p in raw_dir.rglob("*")
        if p.is_file() and p.suffix.lower() in AUDIO_EXTENSIONS
    ]
    return sorted(files)


def normalize_dbfs(audio: AudioSegment, target_dbfs: float) -> AudioSegment:
    if audio.dBFS == float("-inf"):
        return audio
    return audio.apply_gain(target_dbfs - audio.dBFS)


def split_audio(audio: AudioSegment, cfg: dict) -> list[AudioSegment]:
    from pydub.silence import split_on_silence

    chunks = split_on_silence(
        audio,
        min_silence_len=int(cfg["silence_min_ms"]),
        silence_thresh=float(cfg["silence_threshold_db"]),
        keep_silence=int(cfg["keep_silence_ms"]),
    )
    return chunks or [audio]


def fit_segment_lengths(
    chunks: list[AudioSegment],
    min_ms: int,
    max_ms: int,
) -> list[AudioSegment]:
    from pydub import AudioSegment

    merged: list[AudioSegment] = []
    current = AudioSegment.silent(duration=0)

    for chunk in chunks:
        if len(chunk) > max_ms:
            if len(current) >= min_ms:
                merged.append(current)
            current = AudioSegment.silent(duration=0)
            for start in range(0, len(chunk), max_ms):
                part = chunk[start:start + max_ms]
                if len(part) >= min_ms:
                    merged.append(part)
            continue

        if len(current) == 0:
            current = chunk
        elif len(current) + len(chunk) <= max_ms:
            current += chunk
        else:
            if len(current) >= min_ms:
                merged.append(current)
            current = chunk

    if len(current) >= min_ms:
        merged.append(current)

    return [seg for seg in merged if min_ms <= len(seg) <= max_ms]


def process_file(
    src: Path,
    file_index: int,
    cfg: dict,
    speaker: str,
    sliced_dir: Path,
) -> list[dict]:
    from pydub import AudioSegment

    audio = AudioSegment.from_file(src)
    audio = audio.set_channels(int(cfg["channels"])).set_frame_rate(int(cfg["sample_rate"]))
    audio = normalize_dbfs(audio, float(cfg["target_dbfs"]))

    raw_chunks = split_audio(audio, cfg)
    segments = fit_segment_lengths(
        raw_chunks,
        min_ms=int(float(cfg["min_segment_sec"]) * 1000),
        max_ms=int(float(cfg["max_segment_sec"]) * 1000),
    )

    rows: list[dict] = []
    for segment_index, segment in enumerate(segments, start=1):
        dbfs = segment.dBFS
        if dbfs == float("-inf"):
            continue
        if dbfs < float(cfg["min_dbfs"]) or dbfs > float(cfg["max_dbfs"]):
            continue

        out_name = f"{speaker}_{file_index:04d}_{segment_index:04d}.wav"
        out_path = sliced_dir / out_name
        segment.export(out_path, format="wav")
        rows.append({
            "audio_path": rel_path(out_path),
            "source_path": rel_path(src),
            "duration_sec": f"{len(segment) / 1000:.3f}",
            "dbfs": f"{dbfs:.2f}",
            "sample_rate": cfg["sample_rate"],
        })

    return rows


def write_metadata(rows: list[dict], transcript_dir: Path) -> None:
    transcript_dir.mkdir(parents=True, exist_ok=True)
    metadata_path = transcript_dir / "segments.csv"
    with open(metadata_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["audio_path", "source_path", "duration_sec", "dbfs", "sample_rate"],
        )
        writer.writeheader()
        writer.writerows(rows)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Split and normalize raw voice recordings.")
    parser.add_argument("--clean", action="store_true", help="Delete existing data/sliced before processing.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config = load_config()
    paths = config["paths"]
    cfg = config["preprocess"]
    speaker = config["speaker"]["name"]

    raw_dir = ROOT / paths["raw_dir"]
    sliced_dir = ROOT / paths["sliced_dir"]
    transcript_dir = ROOT / paths["transcript_dir"]

    print(f"\n{Fore.CYAN}Step 1: prepare audio segments{Style.RESET_ALL}")
    check_ffmpeg()

    if not raw_dir.exists():
        raw_dir.mkdir(parents=True)
        raise SystemExit(f"已建立 {rel_path(raw_dir)}，請先把 mp3/wav 放進去。")

    audio_files = find_audio_files(raw_dir)
    if not audio_files:
        raise SystemExit(f"{rel_path(raw_dir)} 裡沒有可處理的音檔。")

    if args.clean and sliced_dir.exists():
        shutil.rmtree(sliced_dir)
    sliced_dir.mkdir(parents=True, exist_ok=True)

    all_rows: list[dict] = []
    for index, src in enumerate(tqdm(audio_files, desc="Processing", unit="file"), start=1):
        try:
            rows = process_file(src, index, cfg, speaker, sliced_dir)
            all_rows.extend(rows)
        except Exception as exc:
            log.warning("跳過 %s：%s", rel_path(src), exc)

    write_metadata(all_rows, transcript_dir)

    total_minutes = sum(float(row["duration_sec"]) for row in all_rows) / 60
    print(f"\n完成：{len(all_rows)} 段，約 {total_minutes:.1f} 分鐘")
    print(f"輸出：{rel_path(sliced_dir)}")
    print(f"metadata：{rel_path(transcript_dir / 'segments.csv')}")

    quality = config["quality"]
    if total_minutes < float(quality["min_total_minutes"]):
        print(f"{Fore.YELLOW}提醒：可用語音少於 {quality['min_total_minutes']} 分鐘，fine-tune 品質可能有限。{Style.RESET_ALL}")


if __name__ == "__main__":
    main()
