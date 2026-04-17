#!/usr/bin/env python3
"""
Step 3: 資料集校稿工具
- 顯示每段音訊的自動轉錄結果
- 讓你播放音訊並校正錯誤文字
- 標記並移除品質差的片段
- 產出最終的訓練清單
"""

import os
import sys
import yaml
import argparse
import subprocess
from pathlib import Path
from colorama import init, Fore, Style

init()

# ── 路徑設定 ──────────────────────────────────────────
ROOT = Path(__file__).parent.parent
CONFIG_PATH = ROOT / "configs" / "voice_config.yaml"
TRANSCRIPT_DIR = ROOT / "data" / "transcripts"
DATASET_LIST = TRANSCRIPT_DIR / "dataset_list.txt"
VALIDATED_LIST = TRANSCRIPT_DIR / "dataset_validated.txt"
REJECTED_LIST = TRANSCRIPT_DIR / "dataset_rejected.txt"

with open(CONFIG_PATH, encoding="utf-8") as f:
    config = yaml.safe_load(f)


def print_header():
    print(f"\n{Fore.CYAN}{'='*55}")
    print("  Step 3: 資料集校稿")
    print(f"{'='*55}{Style.RESET_ALL}")
    print("""
操作說明：
  [Enter]   → 保留此筆（轉錄正確）
  [e]       → 編輯文字（有錯字時）
  [d]       → 刪除此筆（音質差/轉錄嚴重錯誤）
  [p]       → 播放音訊（需要 ffplay）
  [s]       → 儲存並離開（下次繼續）
  [q]       → 放棄並離開（不儲存）
""")


def parse_dataset_list(filepath: Path) -> list[dict]:
    """解析訓練清單"""
    entries = []
    with open(filepath, encoding="utf-8") as f:
        for line_no, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            parts = line.split("|")
            if len(parts) < 4:
                continue
            entries.append({
                "line_no": line_no,
                "audio_path": parts[0],
                "speaker": parts[1],
                "lang": parts[2],
                "text": parts[3],
                "status": "pending",  # pending / keep / edit / delete
            })
    return entries


def play_audio(audio_path: str):
    """播放音訊（使用 ffplay）"""
    try:
        subprocess.run(
            ["ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet", audio_path],
            timeout=30,
            check=False,
        )
    except FileNotFoundError:
        print(f"  {Fore.YELLOW}[提示] 找不到 ffplay，無法播放音訊{Style.RESET_ALL}")
    except subprocess.TimeoutExpired:
        print(f"  {Fore.YELLOW}[提示] 播放超時{Style.RESET_ALL}")


def get_stats(entries: list[dict]) -> dict:
    """統計各狀態數量"""
    stats = {"pending": 0, "keep": 0, "edit": 0, "delete": 0}
    for e in entries:
        stats[e["status"]] += 1
    return stats


def save_progress(entries: list[dict]):
    """儲存已處理的結果"""
    validated = []
    rejected = []

    for e in entries:
        if e["status"] == "delete":
            rejected.append(e)
        elif e["status"] in ("keep", "edit"):
            validated.append(e)
        # pending 的不管（等下次繼續）

    # 寫入已驗證清單（keep + edit）
    with open(VALIDATED_LIST, "w", encoding="utf-8") as f:
        for e in validated:
            f.write(f"{e['audio_path']}|{e['speaker']}|{e['lang']}|{e['text']}\n")

    # 寫入已驗證 + pending（保存完整進度）
    progress_path = TRANSCRIPT_DIR / "dataset_progress.txt"
    with open(progress_path, "w", encoding="utf-8") as f:
        for e in entries:
            status_marker = f"[{e['status'].upper()}]"
            f.write(f"{status_marker}|{e['audio_path']}|{e['speaker']}|{e['lang']}|{e['text']}\n")

    return len(validated), len(rejected)


def load_progress(entries: list[dict]) -> list[dict]:
    """讀取上次的進度"""
    progress_path = TRANSCRIPT_DIR / "dataset_progress.txt"
    if not progress_path.exists():
        return entries

    progress = {}
    with open(progress_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            parts = line.split("|")
            if len(parts) < 5:
                continue
            status_marker = parts[0]
            audio_path = parts[1]
            text = parts[4]
            status = status_marker.strip("[]").lower()
            if status in ("keep", "edit", "delete", "pending"):
                progress[audio_path] = {"status": status, "text": text}

    # 套用進度
    for e in entries:
        if e["audio_path"] in progress:
            e["status"] = progress[e["audio_path"]]["status"]
            e["text"] = progress[e["audio_path"]]["text"]

    return entries


def print_stats(entries: list[dict]):
    stats = get_stats(entries)
    total = len(entries)
    done = stats["keep"] + stats["edit"] + stats["delete"]
    pct = done / total * 100 if total > 0 else 0

    print(f"\n  進度: {done}/{total} ({pct:.1f}%)")
    print(f"  保留: {Fore.GREEN}{stats['keep'] + stats['edit']}{Style.RESET_ALL}  "
          f"刪除: {Fore.RED}{stats['delete']}{Style.RESET_ALL}  "
          f"待處理: {Fore.YELLOW}{stats['pending']}{Style.RESET_ALL}\n")


def validate_interactive(entries: list[dict]):
    """互動式校稿介面"""
    pending = [e for e in entries if e["status"] == "pending"]
    total = len(entries)

    if not pending:
        print(f"{Fore.GREEN}所有資料已完成校稿！{Style.RESET_ALL}")
        print_stats(entries)
        return

    print(f"待校稿: {Fore.YELLOW}{len(pending)}{Style.RESET_ALL} 筆\n")

    for i, entry in enumerate(pending):
        # 顯示進度
        done = len(entries) - len([e for e in entries if e["status"] == "pending"])
        print(f"{'─'*55}")
        print(f"  [{done+1}/{total}] {Fore.CYAN}{Path(entry['audio_path']).name}{Style.RESET_ALL}")
        print(f"  轉錄: {Fore.YELLOW}{entry['text']}{Style.RESET_ALL}")
        print(f"{'─'*55}")

        while True:
            choice = input("  操作 [Enter/e/d/p/s/q]: ").strip().lower()

            if choice == "":
                entry["status"] = "keep"
                break
            elif choice == "e":
                new_text = input(f"  輸入正確文字: ").strip()
                if new_text:
                    entry["text"] = new_text
                    entry["status"] = "edit"
                    print(f"  {Fore.GREEN}✓ 已更新{Style.RESET_ALL}")
                break
            elif choice == "d":
                entry["status"] = "delete"
                print(f"  {Fore.RED}✗ 已標記刪除{Style.RESET_ALL}")
                break
            elif choice == "p":
                print(f"  播放中...")
                play_audio(entry["audio_path"])
            elif choice == "s":
                print(f"\n{Fore.YELLOW}儲存進度並離開...{Style.RESET_ALL}")
                return
            elif choice == "q":
                print(f"\n{Fore.RED}放棄修改，離開{Style.RESET_ALL}")
                sys.exit(0)
            else:
                print(f"  請輸入有效的操作指令")


def print_final_summary(validated_count: int, rejected_count: int):
    print(f"\n{Fore.CYAN}{'='*55}")
    print(f"  校稿完成！")
    print(f"{'='*55}{Style.RESET_ALL}")
    print(f"  有效訓練資料: {Fore.GREEN}{validated_count} 筆{Style.RESET_ALL}")
    print(f"  已移除:       {Fore.RED}{rejected_count} 筆{Style.RESET_ALL}")
    print(f"  輸出位置: {VALIDATED_LIST}")

    if validated_count < 100:
        print(f"\n{Fore.YELLOW}[警告] 有效資料少於 100 筆，建議補充更多錄音{Style.RESET_ALL}")
    elif validated_count >= 300:
        print(f"\n{Fore.GREEN}[良好] 資料量充足，可開始訓練！{Style.RESET_ALL}")

    print(f"\n{Fore.CYAN}下一步: 執行訓練腳本{Style.RESET_ALL}")
    print(f"  方式 A: 打開 GPT-SoVITS WebUI 進行訓練（推薦）")
    print(f"  方式 B: python scripts/04_launch_training.bat\n")


def skip_validation(entries: list[dict]):
    """跳過校稿，全部標記為 keep"""
    for e in entries:
        if e["status"] == "pending":
            e["status"] = "keep"


def main():
    parser = argparse.ArgumentParser(description="Step 3: 資料集校稿工具")
    parser.add_argument(
        "--skip",
        action="store_true",
        help="跳過人工校稿，全部保留並直接產出 dataset_validated.txt",
    )
    args = parser.parse_args()

    print_header()

    if not DATASET_LIST.exists():
        print(f"{Fore.RED}[錯誤] 找不到轉錄清單")
        print(f"請先執行: python scripts/02_transcribe.py{Style.RESET_ALL}")
        sys.exit(1)

    # 解析並載入進度
    entries = parse_dataset_list(DATASET_LIST)
    entries = load_progress(entries)

    total = len(entries)
    print(f"共 {Fore.YELLOW}{total}{Style.RESET_ALL} 筆資料\n")

    # ── 跳過模式 ──────────────────────────────────────────
    if args.skip:
        print(f"{Fore.YELLOW}[--skip] 跳過人工校稿，全部資料標記為保留{Style.RESET_ALL}\n")
        skip_validation(entries)
        validated_count, rejected_count = save_progress(entries)
        print_final_summary(validated_count, rejected_count)
        return

    # ── 一般互動流程 ───────────────────────────────────────
    # 顯示統計
    print_stats(entries)

    # 詢問是否繼續
    pending = [e for e in entries if e["status"] == "pending"]
    if not pending:
        print(f"{Fore.GREEN}所有資料已完成校稿！{Style.RESET_ALL}")
    else:
        choice = input(f"開始校稿 {len(pending)} 筆待處理資料？ [Y/n]: ").strip().lower()
        if choice not in ("", "y", "yes"):
            sys.exit(0)

        # 互動式校稿
        validate_interactive(entries)

    # 儲存
    validated_count, rejected_count = save_progress(entries)
    print_final_summary(validated_count, rejected_count)


if __name__ == "__main__":
    main()
