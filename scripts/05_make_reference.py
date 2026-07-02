#!/usr/bin/env python3
"""Create a GPT-SoVITS reference clip from validated training data."""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path

import yaml
from colorama import Fore, Style, init

init()

ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT / "configs" / "voice_config.yaml"


def load_config() -> dict:
    with open(CONFIG_PATH, encoding="utf-8") as f:
        return yaml.safe_load(f)


def save_config(config: dict) -> None:
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        yaml.safe_dump(config, f, allow_unicode=True, sort_keys=False)


def parse_dataset_line(line: str) -> dict | None:
    parts = line.rstrip("\n").split("|", 3)
    if len(parts) != 4:
        return None
    return {"audio_path": Path(parts[0]), "speaker": parts[1], "lang": parts[2], "text": parts[3]}


def load_validated(path: Path) -> list[dict]:
    entries: list[dict] = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            entry = parse_dataset_line(line)
            if entry:
                entries.append(entry)
    return entries


def duration_sec(path: Path) -> float:
    from pydub import AudioSegment

    return len(AudioSegment.from_file(path)) / 1000


def choose_reference(entries: list[dict], cfg: dict) -> dict:
    scored: list[tuple[float, dict]] = []
    for entry in entries:
        path = entry["audio_path"]
        if not path.exists():
            continue
        try:
            sec = duration_sec(path)
        except Exception:
            continue
        text_len = len(entry["text"])
        if not (float(cfg["preferred_min_sec"]) <= sec <= float(cfg["preferred_max_sec"])):
            continue
        if not (int(cfg["preferred_min_chars"]) <= text_len <= int(cfg["preferred_max_chars"])):
            continue

        target_sec = (float(cfg["preferred_min_sec"]) + float(cfg["preferred_max_sec"])) / 2
        score = abs(sec - target_sec) + abs(text_len - 24) / 20
        scored.append((score, {**entry, "duration_sec": sec}))

    if not scored:
        raise SystemExit("找不到合適 reference。請挑一段 5-10 秒、文字正確、乾淨的音檔手動指定。")

    scored.sort(key=lambda item: item[0])
    return scored[0][1]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create data/reference/ref.wav and ref.txt.")
    parser.add_argument("--audio", help="Manually selected reference wav/mp3.")
    parser.add_argument("--text", help="Text spoken in --audio.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config = load_config()
    ref_cfg = config["reference"]
    transcript_dir = ROOT / config["paths"]["transcript_dir"]
    validated_path = transcript_dir / "dataset_validated.txt"
    ref_audio = ROOT / ref_cfg["audio"]
    ref_text_file = ROOT / ref_cfg["text_file"]
    ref_audio.parent.mkdir(parents=True, exist_ok=True)

    print(f"\n{Fore.CYAN}Step 5: create reference clip{Style.RESET_ALL}")

    if args.audio:
        if not args.text:
            raise SystemExit("使用 --audio 時也需要 --text。")
        chosen = {"audio_path": Path(args.audio), "text": args.text, "duration_sec": duration_sec(Path(args.audio))}
    else:
        if not validated_path.exists():
            raise SystemExit("找不到 dataset_validated.txt，請先執行 Step 3。")
        chosen = choose_reference(load_validated(validated_path), ref_cfg)

    if not chosen["audio_path"].exists():
        raise SystemExit(f"找不到 reference 音檔：{chosen['audio_path']}")

    shutil.copy2(chosen["audio_path"], ref_audio)
    with open(ref_text_file, "w", encoding="utf-8") as f:
        f.write(chosen["text"].strip() + "\n")

    config["inference"]["reference_audio"] = ref_cfg["audio"]
    config["inference"]["reference_text"] = chosen["text"].strip()
    save_config(config)

    print(f"reference audio：{ref_audio}")
    print(f"reference text：{chosen['text']}")
    print(f"duration：{chosen['duration_sec']:.2f} sec")


if __name__ == "__main__":
    main()
