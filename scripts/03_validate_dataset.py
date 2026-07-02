#!/usr/bin/env python3
"""Review Whisper transcripts and create dataset_validated.txt."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

import yaml
from colorama import Fore, Style, init

init()

ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT / "configs" / "voice_config.yaml"


def load_config() -> dict:
    with open(CONFIG_PATH, encoding="utf-8") as f:
        return yaml.safe_load(f)


def parse_dataset_line(line: str) -> dict | None:
    parts = line.rstrip("\n").split("|", 3)
    if len(parts) != 4:
        return None
    return {
        "audio_path": parts[0],
        "speaker": parts[1],
        "lang": parts[2],
        "text": parts[3],
        "status": "pending",
    }


def load_dataset(path: Path) -> list[dict]:
    entries: list[dict] = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            entry = parse_dataset_line(line)
            if entry:
                entries.append(entry)
    return entries


def progress_path(transcript_dir: Path) -> Path:
    return transcript_dir / "dataset_progress.tsv"


def load_progress(entries: list[dict], transcript_dir: Path) -> None:
    path = progress_path(transcript_dir)
    if not path.exists():
        return
    progress: dict[str, tuple[str, str]] = {}
    with open(path, encoding="utf-8") as f:
        for line in f:
            parts = line.rstrip("\n").split("\t", 2)
            if len(parts) == 3:
                progress[parts[0]] = (parts[1], parts[2])
    for entry in entries:
        if entry["audio_path"] in progress:
            entry["status"], entry["text"] = progress[entry["audio_path"]]


def save_entries(entries: list[dict], transcript_dir: Path) -> tuple[int, int]:
    transcript_dir.mkdir(parents=True, exist_ok=True)
    validated_path = transcript_dir / "dataset_validated.txt"
    rejected_path = transcript_dir / "dataset_rejected.txt"

    valid = [e for e in entries if e["status"] in {"keep", "edit"}]
    rejected = [e for e in entries if e["status"] == "delete"]

    with open(validated_path, "w", encoding="utf-8") as f:
        for e in valid:
            f.write(f"{e['audio_path']}|{e['speaker']}|{e['lang']}|{e['text']}\n")

    with open(rejected_path, "w", encoding="utf-8") as f:
        for e in rejected:
            f.write(f"{e['audio_path']}|{e['speaker']}|{e['lang']}|{e['text']}\n")

    with open(progress_path(transcript_dir), "w", encoding="utf-8") as f:
        for e in entries:
            f.write(f"{e['audio_path']}\t{e['status']}\t{e['text']}\n")

    return len(valid), len(rejected)


def play_audio(audio_path: str) -> None:
    try:
        subprocess.run(
            ["ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet", audio_path],
            timeout=30,
            check=False,
        )
    except FileNotFoundError:
        print(f"{Fore.YELLOW}找不到 ffplay，請確認 ffmpeg 已安裝。{Style.RESET_ALL}")
    except subprocess.TimeoutExpired:
        print(f"{Fore.YELLOW}播放逾時，已停止。{Style.RESET_ALL}")


def stats(entries: list[dict]) -> str:
    keep = sum(1 for e in entries if e["status"] in {"keep", "edit"})
    delete = sum(1 for e in entries if e["status"] == "delete")
    pending = sum(1 for e in entries if e["status"] == "pending")
    return f"保留 {keep} / 刪除 {delete} / 未審 {pending}"


def interactive_review(entries: list[dict], transcript_dir: Path) -> None:
    pending = [e for e in entries if e["status"] == "pending"]
    total = len(entries)
    print("操作：Enter=保留, e=改字, d=刪除, p=播放, s=存檔離開, q=不存離開")

    for entry in pending:
        done = total - sum(1 for e in entries if e["status"] == "pending")
        print("\n" + "-" * 72)
        print(f"[{done + 1}/{total}] {Path(entry['audio_path']).name}")
        print(f"文字：{Fore.YELLOW}{entry['text']}{Style.RESET_ALL}")
        print("-" * 72)

        while True:
            choice = input("選擇 [Enter/e/d/p/s/q]: ").strip().lower()
            if choice == "":
                entry["status"] = "keep"
                break
            if choice == "e":
                new_text = input("新的文字: ").strip()
                if new_text:
                    entry["text"] = new_text
                    entry["status"] = "edit"
                break
            if choice == "d":
                entry["status"] = "delete"
                break
            if choice == "p":
                play_audio(entry["audio_path"])
                continue
            if choice == "s":
                save_entries(entries, transcript_dir)
                print(f"已存檔：{stats(entries)}")
                return
            if choice == "q":
                raise SystemExit("未存檔離開。")
            print("無效選項。")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate transcript dataset.")
    parser.add_argument("--skip", action="store_true", help="Accept all pending lines without interactive review.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config = load_config()
    transcript_dir = ROOT / config["paths"]["transcript_dir"]
    dataset_path = transcript_dir / "dataset_list.txt"

    print(f"\n{Fore.CYAN}Step 3: validate dataset{Style.RESET_ALL}")
    if not dataset_path.exists():
        raise SystemExit("找不到 data/transcripts/dataset_list.txt，請先執行 Step 2。")

    entries = load_dataset(dataset_path)
    load_progress(entries, transcript_dir)
    if not entries:
        raise SystemExit("dataset_list.txt 沒有可用資料。")

    print(f"資料筆數：{len(entries)}，{stats(entries)}")

    if args.skip:
        for entry in entries:
            if entry["status"] == "pending":
                entry["status"] = "keep"
    else:
        interactive_review(entries, transcript_dir)

    valid, rejected = save_entries(entries, transcript_dir)
    print(f"\n完成：保留 {valid}，刪除 {rejected}")
    print("下一步：python scripts/05_make_reference.py")


if __name__ == "__main__":
    main()
