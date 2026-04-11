#!/usr/bin/env python3
"""
Step 1: 音訊前處理
- 掃描 data/raw/ 下的所有 MP3 檔案
- 轉換為 WAV（16kHz, 單聲道）
- 正規化音量
- 依靜音切段（每段 3~10 秒）
- 輸出到 data/sliced/
"""

import os
import sys
import yaml
import logging
from pathlib import Path
from tqdm import tqdm
from colorama import init, Fore, Style

# 初始化 colorama（Windows 色彩支援）
init()

# ── 路徑設定 ──────────────────────────────────────────
ROOT = Path(__file__).parent.parent
CONFIG_PATH = ROOT / "configs" / "voice_config.yaml"
RAW_DIR = ROOT / "data" / "raw"
SLICED_DIR = ROOT / "data" / "sliced"

# ── 載入設定 ──────────────────────────────────────────
with open(CONFIG_PATH, encoding="utf-8") as f:
    config = yaml.safe_load(f)

cfg = config["preprocess"]
SAMPLE_RATE = cfg["sample_rate"]
MIN_SEC = cfg["min_segment_sec"]
MAX_SEC = cfg["max_segment_sec"]
TARGET_DB = cfg["target_db"]
SILENCE_DB = cfg["silence_threshold_db"]
SILENCE_MS = cfg["silence_min_ms"]
SPEAKER = config["speaker"]["name"]

# ── 日誌設定 ──────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)


def print_header():
    print(f"\n{Fore.CYAN}{'='*50}")
    print("  Step 1: 音訊前處理")
    print(f"{'='*50}{Style.RESET_ALL}\n")


def check_ffmpeg():
    """確認 ffmpeg 已安裝"""
    import shutil
    if not shutil.which("ffmpeg"):
        print(f"{Fore.RED}[錯誤] 找不到 ffmpeg！")
        print("請下載並安裝 ffmpeg: https://ffmpeg.org/download.html")
        print("安裝後確認 ffmpeg 在 PATH 中{Style.RESET_ALL}")
        sys.exit(1)
    print(f"{Fore.GREEN}[OK] ffmpeg 已就緒{Style.RESET_ALL}")


def get_audio_files() -> list[Path]:
    """掃描 raw 資料夾，取得所有音訊檔案"""
    extensions = [".mp3", ".wav", ".m4a", ".aac", ".flac", ".ogg"]
    files = []
    for ext in extensions:
        files.extend(RAW_DIR.glob(f"*{ext}"))
        files.extend(RAW_DIR.glob(f"**/*{ext}"))  # 支援子資料夾

    files = sorted(set(files))
    return files


def normalize_audio(audio):
    """正規化音量到目標 dBFS"""
    from pydub import AudioSegment
    change_in_dBFS = TARGET_DB - audio.dBFS
    return audio.apply_gain(change_in_dBFS)


def slice_on_silence(audio, min_silence_ms: int, silence_db: float):
    """依靜音切段音訊"""
    from pydub.silence import split_on_silence

    chunks = split_on_silence(
        audio,
        min_silence_len=min_silence_ms,
        silence_thresh=silence_db,
        keep_silence=200,  # 保留 200ms 靜音作緩衝
    )
    return chunks


def merge_short_chunks(chunks, min_ms: float, max_ms: float):
    """
    合併太短的片段，切分太長的片段
    目標：每段 min_ms ~ max_ms 毫秒
    """
    min_ms = int(min_ms * 1000)
    max_ms = int(max_ms * 1000)

    merged = []
    current = None

    for chunk in chunks:
        if current is None:
            current = chunk
        elif len(current) + len(chunk) <= max_ms:
            current = current + chunk
        else:
            if len(current) >= min_ms:
                merged.append(current)
            current = chunk

    if current is not None and len(current) >= min_ms:
        merged.append(current)

    # 切分過長的片段
    result = []
    for chunk in merged:
        if len(chunk) <= max_ms:
            result.append(chunk)
        else:
            # 強制切割
            start = 0
            while start < len(chunk):
                end = min(start + max_ms, len(chunk))
                part = chunk[start:end]
                if len(part) >= min_ms:
                    result.append(part)
                start = end

    return result


def process_file(src_path: Path, file_idx: int) -> list[Path]:
    """處理單一音訊檔案，返回切段後的檔案路徑列表"""
    from pydub import AudioSegment

    try:
        # 載入音訊
        audio = AudioSegment.from_file(str(src_path))

        # 轉換：單聲道 + 目標取樣率
        audio = audio.set_channels(1).set_frame_rate(SAMPLE_RATE)

        # 正規化音量
        audio = normalize_audio(audio)

        # 切段
        chunks = slice_on_silence(audio, SILENCE_MS, SILENCE_DB)

        if not chunks:
            log.warning(f"  {src_path.name}: 找不到靜音切點，整段保留")
            chunks = [audio]

        # 合併/調整長度
        chunks = merge_short_chunks(chunks, MIN_SEC, MAX_SEC)

        if not chunks:
            log.warning(f"  {src_path.name}: 處理後無有效片段，跳過")
            return []

        # 儲存切段
        saved = []
        for seg_idx, chunk in enumerate(chunks, start=1):
            out_name = f"{SPEAKER}_{file_idx:04d}_{seg_idx:04d}.wav"
            out_path = SLICED_DIR / out_name
            chunk.export(str(out_path), format="wav")
            saved.append(out_path)

        total_sec = sum(len(c) for c in chunks) / 1000
        log.info(f"  {src_path.name}: {len(chunks)} 段, 共 {total_sec:.1f} 秒")
        return saved

    except Exception as e:
        log.error(f"  {src_path.name}: 處理失敗 — {e}")
        return []


def print_summary(all_segments: list[Path]):
    """輸出統計摘要"""
    from pydub import AudioSegment

    total_files = len(all_segments)
    if total_files == 0:
        print(f"\n{Fore.RED}沒有產生任何切段，請確認 data/raw/ 中有音訊檔案{Style.RESET_ALL}")
        return

    # 計算總時長
    total_ms = 0
    for seg_path in all_segments:
        try:
            audio = AudioSegment.from_wav(str(seg_path))
            total_ms += len(audio)
        except:
            pass

    total_min = total_ms / 1000 / 60

    print(f"\n{Fore.GREEN}{'='*50}")
    print(f"  前處理完成！")
    print(f"{'='*50}{Style.RESET_ALL}")
    print(f"  切段數量: {Fore.YELLOW}{total_files} 段{Style.RESET_ALL}")
    print(f"  總時長:   {Fore.YELLOW}{total_min:.1f} 分鐘{Style.RESET_ALL}")
    print(f"  輸出位置: {SLICED_DIR}")
    print()

    if total_min < 30:
        print(f"{Fore.YELLOW}[建議] 訓練資料少於 30 分鐘，品質可能不穩定")
        print(f"建議補充更多錄音到 data/raw/{Style.RESET_ALL}")
    elif total_min >= 60:
        print(f"{Fore.GREEN}[良好] 訓練資料充足（{total_min:.0f} 分鐘），預期品質優秀！{Style.RESET_ALL}")

    print(f"\n{Fore.CYAN}下一步: python scripts/02_transcribe.py{Style.RESET_ALL}\n")


def main():
    print_header()
    check_ffmpeg()

    # 確認目錄
    if not RAW_DIR.exists():
        RAW_DIR.mkdir(parents=True)
        print(f"{Fore.YELLOW}[提示] 已建立 data/raw/ 資料夾")
        print(f"請將你的 MP3 檔案放入 data/raw/ 後再執行此腳本{Style.RESET_ALL}")
        sys.exit(0)

    SLICED_DIR.mkdir(parents=True, exist_ok=True)

    # 掃描音訊檔案
    audio_files = get_audio_files()
    if not audio_files:
        print(f"{Fore.RED}[錯誤] data/raw/ 中找不到音訊檔案")
        print(f"支援格式: mp3, wav, m4a, aac, flac, ogg{Style.RESET_ALL}")
        sys.exit(1)

    print(f"找到 {Fore.YELLOW}{len(audio_files)}{Style.RESET_ALL} 個音訊檔案\n")

    # 處理每個檔案
    all_segments = []
    for idx, audio_file in enumerate(tqdm(audio_files, desc="處理中", unit="檔"), start=1):
        segments = process_file(audio_file, idx)
        all_segments.extend(segments)

    # 輸出摘要
    print_summary(all_segments)


if __name__ == "__main__":
    main()
