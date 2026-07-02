#!/usr/bin/env python3
"""Generate speech with the fine-tuned GPT-SoVITS model."""

from __future__ import annotations

import argparse
import datetime as dt
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


def read_reference_text(config: dict) -> str:
    text = config["inference"].get("reference_text") or ""
    ref_text_file = ROOT / config["reference"]["text_file"]
    if not text and ref_text_file.exists():
        text = ref_text_file.read_text(encoding="utf-8").strip()
    return text


def check_paths(config: dict) -> None:
    missing = []
    for label, key in [("SoVITS", "sovits_model_path"), ("GPT", "gpt_model_path")]:
        path = ROOT / config["inference"][key]
        if not path.exists():
            missing.append(f"{label}: {path}")
    ref_audio = ROOT / config["inference"]["reference_audio"]
    if not ref_audio.exists():
        missing.append(f"Reference audio: {ref_audio}")
    if missing:
        raise SystemExit("缺少必要檔案：\n" + "\n".join(f"  - {item}" for item in missing))


def load_tts(config: dict):
    gptsovits_dir = ROOT / config["paths"]["gptsovits_dir"]
    if not gptsovits_dir.exists():
        raise SystemExit(f"找不到 GPT-SoVITS：{gptsovits_dir}。請先執行 setup\\install.bat。")
    sys.path.insert(0, str(gptsovits_dir))

    try:
        from GPT_SoVITS.TTS_infer_pack.TTS import TTS, TTS_Config
    except ImportError as exc:
        raise SystemExit("無法匯入 GPT-SoVITS TTS。請確認 GPT-SoVITS 已安裝且依賴完整。") from exc

    tts_config_path = gptsovits_dir / "configs" / "tts_infer.yaml"
    tts_config = TTS_Config(str(tts_config_path))
    tts_config.sovits_path = str(ROOT / config["inference"]["sovits_model_path"])
    tts_config.gpt_path = str(ROOT / config["inference"]["gpt_model_path"])
    return TTS(tts_config)


def generate_one(tts, text: str, config: dict, output_path: Path) -> Path:
    import numpy as np
    import soundfile as sf

    infer = config["inference"]
    lang = config["speaker"]["language"]
    ref_audio = str(ROOT / infer["reference_audio"])
    ref_text = read_reference_text(config)

    inputs = {
        "text": text,
        "text_lang": lang,
        "ref_audio_path": ref_audio,
        "prompt_text": ref_text,
        "prompt_lang": lang,
        "top_k": int(infer["top_k"]),
        "top_p": float(infer["top_p"]),
        "temperature": float(infer["temperature"]),
        "text_split_method": infer.get("text_split_method", "cut5"),
        "batch_size": 1,
        "speed_factor": float(infer["speed_factor"]),
        "ref_text_free": not bool(ref_text),
        "split_bucket": True,
    }

    chunks = []
    sample_rate = None
    for sample_rate, chunk in tts.run(inputs):
        chunks.append(chunk)

    if not chunks or sample_rate is None:
        raise RuntimeError("GPT-SoVITS 沒有回傳音訊。")

    audio = np.concatenate(chunks)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    sf.write(str(output_path), audio, sample_rate)
    return output_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="GPT-SoVITS inference CLI.")
    parser.add_argument("--text", "-t", help="Text to synthesize.")
    parser.add_argument("--file", "-f", help="Text file. Each non-empty line becomes one audio file.")
    parser.add_argument("--out", "-o", help="Output wav path for --text.")
    parser.add_argument("--speed", "-s", type=float, help="Override speed factor.")
    parser.add_argument("--temperature", type=float, help="Override temperature.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if not args.text and not args.file:
        raise SystemExit("請提供 --text 或 --file。")

    config = load_config()
    if args.speed is not None:
        config["inference"]["speed_factor"] = args.speed
    if args.temperature is not None:
        config["inference"]["temperature"] = args.temperature

    check_paths(config)
    print(f"{Fore.CYAN}載入 GPT-SoVITS 模型...{Style.RESET_ALL}")
    tts = load_tts(config)

    output_dir = ROOT / config["paths"]["output_dir"]
    timestamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")

    if args.file:
        input_path = Path(args.file)
        if not input_path.exists():
            raise SystemExit(f"找不到文字檔：{input_path}")
        lines = [line.strip() for line in input_path.read_text(encoding="utf-8").splitlines() if line.strip()]
        for index, line in enumerate(lines, start=1):
            out_path = output_dir / f"output_{timestamp}_{index:03d}.wav"
            generate_one(tts, line, config, out_path)
            print(f"[{index}/{len(lines)}] {out_path}")
        return

    out_path = Path(args.out) if args.out else output_dir / f"output_{timestamp}.wav"
    generate_one(tts, args.text.strip(), config, out_path)
    print(f"完成：{out_path}")


if __name__ == "__main__":
    main()
