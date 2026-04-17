#!/usr/bin/env python3
"""
Step 2: 自動語音轉錄（ASR）
- 使用 Faster-Whisper large-v3 模型
- 轉錄 data/sliced/ 中所有 WAV 片段
- 輸出 data/transcripts/dataset_list.txt（GPT-SoVITS 訓練格式）
"""

import os
import sys
import yaml
import logging
from pathlib import Path
from tqdm import tqdm
from colorama import init, Fore, Style

init()

# ── 路徑設定 ──────────────────────────────────────────
ROOT = Path(__file__).parent.parent
CONFIG_PATH = ROOT / "configs" / "voice_config.yaml"
SLICED_DIR = ROOT / "data" / "sliced"
TRANSCRIPT_DIR = ROOT / "data" / "transcripts"
DATASET_LIST = TRANSCRIPT_DIR / "dataset_list.txt"
FAILED_LOG = TRANSCRIPT_DIR / "failed.txt"

# ── 載入設定 ──────────────────────────────────────────
with open(CONFIG_PATH, encoding="utf-8") as f:
    config = yaml.safe_load(f)

cfg = config["transcribe"]
MODEL_SIZE = cfg["model_size"]
DEVICE = cfg["device"]
COMPUTE_TYPE = cfg["compute_type"]
LANGUAGE = cfg["language"]
BEAM_SIZE = cfg["beam_size"]
VAD_FILTER = cfg["vad_filter"]
SPEAKER = config["speaker"]["name"]
LANG_CODE = config["speaker"]["language"]

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)


def print_header():
    print(f"\n{Fore.CYAN}{'='*50}")
    print("  Step 2: 自動語音轉錄（ASR）")
    print(f"{'='*50}{Style.RESET_ALL}\n")
    print(f"  模型: {Fore.YELLOW}{MODEL_SIZE}{Style.RESET_ALL}")
    print(f"  裝置: {Fore.YELLOW}{DEVICE}{Style.RESET_ALL}")
    print(f"  語言: {Fore.YELLOW}{LANGUAGE}{Style.RESET_ALL}\n")


def load_whisper_model():
    """載入 Faster-Whisper 模型"""
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        print(f"{Fore.RED}[錯誤] 找不到 faster-whisper")
        print(f"請執行: pip install faster-whisper{Style.RESET_ALL}")
        sys.exit(1)

    print(f"正在載入 Whisper {MODEL_SIZE} 模型...")
    print(f"（首次執行會自動下載，約 3GB，請耐心等候）\n")

    try:
        model = WhisperModel(
            MODEL_SIZE,
            device=DEVICE,
            compute_type=COMPUTE_TYPE,
        )
        print(f"{Fore.GREEN}[OK] 模型載入完成{Style.RESET_ALL}\n")
        return model
    except Exception as e:
        log.error(f"模型載入失敗: {e}")
        if "cuda" in str(e).lower():
            print(f"{Fore.YELLOW}[提示] GPU 不可用，改用 CPU 模式（會較慢）{Style.RESET_ALL}")
            model = WhisperModel(MODEL_SIZE, device="cpu", compute_type="int8")
            return model
        raise


def transcribe_file(model, wav_path: Path) -> str | None:
    """轉錄單一 WAV 檔，返回文字（含信心分數過濾）"""
    # 信心分數門檻：avg_logprob 越接近 0 越好，-1.0 以下通常是胡言亂語
    CONFIDENCE_THRESHOLD = cfg.get("confidence_threshold", -0.8)

    try:
        segments, info = model.transcribe(
            str(wav_path),
            language=LANGUAGE,
            beam_size=BEAM_SIZE,
            vad_filter=VAD_FILTER,
            vad_parameters={"min_silence_duration_ms": 500},
        )

        # 合併段落文字，同時過濾低信心段落
        texts = []
        low_confidence_count = 0
        total_count = 0

        for seg in segments:
            total_count += 1
            text = seg.text.strip()
            if not text:
                continue

            # 信心分數過濾（seg.avg_logprob 為負數，越接近 0 越好）
            if seg.avg_logprob < CONFIDENCE_THRESHOLD:
                low_confidence_count += 1
                log.debug(f"低信心段落過濾 ({seg.avg_logprob:.2f}): {text[:20]}")
                continue

            texts.append(text)

        # 若超過一半的段落低信心，整筆放棄
        if total_count > 0 and low_confidence_count / total_count > 0.5:
            log.debug(f"整筆低信心放棄: {wav_path.name}")
            return None

        full_text = "".join(texts).strip()

        # 過濾：太短或疑似錯誤的轉錄
        if len(full_text) < 2:
            return None

        return full_text

    except Exception as e:
        log.error(f"轉錄失敗 {wav_path.name}: {e}")
        return None


def format_dataset_line(wav_path: Path, text: str) -> str:
    """
    GPT-SoVITS 訓練清單格式：
    音訊路徑|說話人名稱|語言代碼|文字
    """
    # 使用相對路徑（方便在 GPU 電腦上調整）
    rel_path = wav_path.resolve()
    return f"{rel_path}|{SPEAKER}|{LANG_CODE}|{text}"


def load_existing_transcripts() -> dict[str, str]:
    """讀取已有的轉錄結果（支援斷點續傳）"""
    existing = {}
    if DATASET_LIST.exists():
        with open(DATASET_LIST, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                parts = line.split("|")
                if len(parts) >= 4:
                    audio_path = parts[0]
                    text = parts[3]
                    filename = Path(audio_path).name
                    existing[filename] = text
    return existing


def main():
    print_header()

    # 確認切段資料夾
    if not SLICED_DIR.exists() or not list(SLICED_DIR.glob("*.wav")):
        print(f"{Fore.RED}[錯誤] data/sliced/ 中找不到 WAV 檔案")
        print(f"請先執行: python scripts/01_preprocess.py{Style.RESET_ALL}")
        sys.exit(1)

    TRANSCRIPT_DIR.mkdir(parents=True, exist_ok=True)

    # 取得所有 WAV 檔案
    wav_files = sorted(SLICED_DIR.glob("*.wav"))
    print(f"找到 {Fore.YELLOW}{len(wav_files)}{Style.RESET_ALL} 個切段\n")

    # 載入已有轉錄（斷點續傳）
    existing = load_existing_transcripts()
    if existing:
        print(f"{Fore.GREEN}[斷點續傳] 已有 {len(existing)} 筆轉錄，跳過已完成的{Style.RESET_ALL}\n")

    # 過濾需要轉錄的檔案
    to_transcribe = [f for f in wav_files if f.name not in existing]
    print(f"需要轉錄: {Fore.YELLOW}{len(to_transcribe)}{Style.RESET_ALL} 個\n")

    if not to_transcribe:
        print(f"{Fore.GREEN}所有檔案已轉錄完成！{Style.RESET_ALL}")
    else:
        # 載入模型
        model = load_whisper_model()

        # 轉錄
        success_count = 0
        failed_files = []

        with open(DATASET_LIST, "a", encoding="utf-8") as out_f, \
             open(FAILED_LOG, "a", encoding="utf-8") as fail_f:

            for wav_path in tqdm(to_transcribe, desc="轉錄中", unit="段"):
                text = transcribe_file(model, wav_path)

                if text:
                    line = format_dataset_line(wav_path, text)
                    out_f.write(line + "\n")
                    out_f.flush()
                    success_count += 1
                else:
                    fail_f.write(str(wav_path) + "\n")
                    failed_files.append(wav_path.name)

        print(f"\n{Fore.GREEN}轉錄完成：成功 {success_count} 筆{Style.RESET_ALL}")
        if failed_files:
            print(f"{Fore.YELLOW}轉錄失敗：{len(failed_files)} 筆（記錄於 data/transcripts/failed.txt）{Style.RESET_ALL}")

    # 統計最終結果
    if DATASET_LIST.exists():
        with open(DATASET_LIST, encoding="utf-8") as f:
            total_lines = sum(1 for line in f if line.strip())

        print(f"\n{Fore.CYAN}{'='*50}")
        print(f"  轉錄清單統計")
        print(f"{'='*50}{Style.RESET_ALL}")
        print(f"  有效轉錄: {Fore.YELLOW}{total_lines} 筆{Style.RESET_ALL}")
        print(f"  輸出位置: {DATASET_LIST}")

        if total_lines < 100:
            print(f"\n{Fore.YELLOW}[警告] 訓練資料偏少（< 100 筆），建議至少 300 筆以上{Style.RESET_ALL}")
        elif total_lines >= 500:
            print(f"\n{Fore.GREEN}[良好] 訓練資料充足（{total_lines} 筆）！{Style.RESET_ALL}")

    print(f"\n{Fore.CYAN}下一步: python scripts/03_validate_dataset.py  （人工校稿）{Style.RESET_ALL}\n")


if __name__ == "__main__":
    main()
