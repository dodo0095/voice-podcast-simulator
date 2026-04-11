#!/usr/bin/env python3
"""
推論 CLI：輸入文字 → 輸出你的聲音 MP3
用法:
  python infer/infer_cli.py --text "你好，這是測試"
  python infer/infer_cli.py --text "你好" --speed 0.9 --out output/hello.wav
  python infer/infer_cli.py --file input.txt  （批次處理）
"""

import sys
import yaml
import argparse
import datetime
from pathlib import Path

# 確保能找到 GPT-SoVITS
ROOT = Path(__file__).parent.parent
GPT_SOVITS_DIR = ROOT / "GPT-SoVITS"
if GPT_SOVITS_DIR.exists():
    sys.path.insert(0, str(GPT_SOVITS_DIR))

from colorama import init, Fore, Style
init()


def load_config():
    config_path = ROOT / "configs" / "voice_config.yaml"
    with open(config_path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def check_models(config: dict) -> bool:
    """檢查模型檔案是否存在"""
    sovits_path = ROOT / config["inference"]["sovits_model_path"]
    gpt_path = ROOT / config["inference"]["gpt_model_path"]

    ok = True
    if not sovits_path.exists():
        print(f"{Fore.RED}[錯誤] 找不到 SoVITS 模型: {sovits_path}")
        print(f"請訓練後將模型複製到 models/ 資料夾{Style.RESET_ALL}")
        ok = False

    if not gpt_path.exists():
        print(f"{Fore.RED}[錯誤] 找不到 GPT 模型: {gpt_path}")
        print(f"請訓練後將模型複製到 models/ 資料夾{Style.RESET_ALL}")
        ok = False

    return ok


def check_reference(config: dict) -> tuple[str, str]:
    """取得參考音訊路徑與文字"""
    ref_audio = ROOT / config["inference"]["reference_audio"]
    ref_text = config["inference"]["reference_text"]

    if not ref_audio.exists():
        print(f"{Fore.RED}[錯誤] 找不到參考音訊: {ref_audio}")
        print(f"請準備一段 3~10 秒的你的聲音，放到 data/reference/ref.wav{Style.RESET_ALL}")
        sys.exit(1)

    if not ref_text:
        print(f"{Fore.YELLOW}[提示] 未設定參考音訊的文字內容")
        print(f"建議在 configs/voice_config.yaml 的 reference_text 填入參考音訊說的話{Style.RESET_ALL}")

    return str(ref_audio), ref_text


def load_tts_engine(config: dict):
    """載入 GPT-SoVITS TTS 引擎"""
    try:
        from GPT_SoVITS.TTS_infer_pack.TTS import TTS, TTS_Config
    except ImportError:
        print(f"{Fore.RED}[錯誤] 無法匯入 GPT-SoVITS")
        print(f"請確認 GPT-SoVITS 已安裝在 {GPT_SOVITS_DIR}{Style.RESET_ALL}")
        sys.exit(1)

    sovits_path = str(ROOT / config["inference"]["sovits_model_path"])
    gpt_path = str(ROOT / config["inference"]["gpt_model_path"])

    # 建立 TTS 設定
    tts_config = TTS_Config(str(GPT_SOVITS_DIR / "configs" / "tts_infer.yaml"))
    tts_config.sovits_path = sovits_path
    tts_config.gpt_path = gpt_path

    print(f"載入模型中...")
    tts = TTS(tts_config)
    print(f"{Fore.GREEN}[OK] 模型載入完成{Style.RESET_ALL}")
    return tts


def generate_audio(
    tts,
    text: str,
    ref_audio: str,
    ref_text: str,
    config: dict,
    output_path: Path,
) -> bool:
    """生成音訊"""
    import soundfile as sf
    import numpy as np

    infer_cfg = config["inference"]
    lang = config["speaker"]["language"]

    try:
        inputs = {
            "text": text,
            "text_lang": lang,
            "ref_audio_path": ref_audio,
            "prompt_text": ref_text,
            "prompt_lang": lang,
            "top_k": infer_cfg["top_k"],
            "top_p": infer_cfg["top_p"],
            "temperature": infer_cfg["temperature"],
            "text_split_method": "cut5",
            "batch_size": 1,
            "speed_factor": infer_cfg["speed_factor"],
            "ref_text_free": not bool(ref_text),
            "split_bucket": True,
        }

        result_generator = tts.run(inputs)

        # 收集音訊資料
        audio_data = []
        sample_rate = None
        for sample_rate, audio_chunk in result_generator:
            audio_data.append(audio_chunk)

        if not audio_data:
            print(f"{Fore.RED}[錯誤] 未產生音訊資料{Style.RESET_ALL}")
            return False

        # 合併並輸出
        audio = np.concatenate(audio_data)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        sf.write(str(output_path), audio, sample_rate)

        duration = len(audio) / sample_rate
        print(f"{Fore.GREEN}✓ 生成完成: {output_path.name} ({duration:.1f} 秒){Style.RESET_ALL}")
        return True

    except Exception as e:
        print(f"{Fore.RED}[錯誤] 生成失敗: {e}{Style.RESET_ALL}")
        return False


def process_text_file(tts, input_file: Path, config: dict, ref_audio: str, ref_text: str):
    """批次處理文字檔（每行一條文案）"""
    output_dir = ROOT / config["inference"]["output_dir"]
    output_dir.mkdir(parents=True, exist_ok=True)

    with open(input_file, encoding="utf-8") as f:
        lines = [line.strip() for line in f if line.strip()]

    print(f"批次處理 {len(lines)} 段文案\n")

    success = 0
    for idx, text in enumerate(lines, start=1):
        timestamp = datetime.datetime.now().strftime("%H%M%S")
        out_path = output_dir / f"output_{idx:03d}_{timestamp}.wav"

        print(f"[{idx}/{len(lines)}] {text[:40]}{'...' if len(text) > 40 else ''}")
        if generate_audio(tts, text, ref_audio, ref_text, config, out_path):
            success += 1

    print(f"\n完成: {success}/{len(lines)} 成功")
    print(f"輸出位置: {output_dir}")


def parse_args():
    parser = argparse.ArgumentParser(
        description="AI 聲音克隆 — 文字轉語音 CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
範例:
  python infer/infer_cli.py --text "大家好，歡迎收聽今天的節目"
  python infer/infer_cli.py --text "你好" --speed 0.9
  python infer/infer_cli.py --file scripts/podcast_script.txt
        """,
    )
    parser.add_argument("--text", "-t", type=str, help="要合成的文字")
    parser.add_argument("--file", "-f", type=str, help="批次處理：文字檔路徑（每行一條）")
    parser.add_argument("--out", "-o", type=str, help="輸出檔案路徑（單一模式）")
    parser.add_argument("--speed", "-s", type=float, help="語速 (0.5~2.0, 預設 1.0)")
    parser.add_argument("--ref-audio", type=str, help="覆蓋參考音訊路徑")
    parser.add_argument("--ref-text", type=str, help="覆蓋參考音訊文字")
    return parser.parse_args()


def main():
    print(f"\n{Fore.CYAN}{'='*45}")
    print(f"  AI 聲音克隆 — CLI 推論")
    print(f"{'='*45}{Style.RESET_ALL}\n")

    args = parse_args()

    if not args.text and not args.file:
        print(f"{Fore.RED}[錯誤] 請提供 --text 或 --file 參數{Style.RESET_ALL}")
        print("範例: python infer/infer_cli.py --text \"大家好\"")
        sys.exit(1)

    # 載入設定
    config = load_config()

    # 覆蓋語速
    if args.speed:
        config["inference"]["speed_factor"] = args.speed

    # 確認模型
    if not check_models(config):
        sys.exit(1)

    # 取得參考音訊
    ref_audio = args.ref_audio or None
    ref_text = args.ref_text or None

    if not ref_audio:
        ref_audio, ref_text_default = check_reference(config)
        ref_text = ref_text or ref_text_default

    # 載入引擎
    tts = load_tts_engine(config)

    # 執行
    if args.file:
        input_file = Path(args.file)
        if not input_file.exists():
            print(f"{Fore.RED}[錯誤] 找不到檔案: {input_file}{Style.RESET_ALL}")
            sys.exit(1)
        process_text_file(tts, input_file, config, ref_audio, ref_text)

    else:
        # 單一文字模式
        output_dir = ROOT / config["inference"]["output_dir"]
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

        if args.out:
            out_path = Path(args.out)
        else:
            out_path = output_dir / f"output_{timestamp}.wav"

        print(f"文字: {Fore.YELLOW}{args.text}{Style.RESET_ALL}")
        print(f"語速: {config['inference']['speed_factor']}\n")

        generate_audio(tts, args.text, ref_audio, ref_text, config, out_path)


if __name__ == "__main__":
    main()
