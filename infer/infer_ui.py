#!/usr/bin/env python3
"""Small Gradio UI for local GPT-SoVITS inference."""

from __future__ import annotations

import datetime as dt
from pathlib import Path

import numpy as np
import yaml

ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT / "configs" / "voice_config.yaml"
_ENGINE = None
_CONFIG = None


def load_config() -> dict:
    with open(CONFIG_PATH, encoding="utf-8") as f:
        return yaml.safe_load(f)


def read_reference_text(config: dict) -> str:
    text = config["inference"].get("reference_text") or ""
    ref_text_file = ROOT / config["reference"]["text_file"]
    if not text and ref_text_file.exists():
        text = ref_text_file.read_text(encoding="utf-8").strip()
    return text


def reference_choices(config: dict) -> list[str]:
    choices = []
    for folder in [ROOT / config["paths"]["reference_dir"], ROOT / config["paths"]["sliced_dir"]]:
        if folder.exists():
            choices.extend(str(p) for p in sorted(folder.glob("*.wav"))[:30])
    return choices


def get_engine():
    global _ENGINE, _CONFIG
    if _ENGINE is not None:
        return _ENGINE, _CONFIG

    import sys

    config = load_config()
    gptsovits_dir = ROOT / config["paths"]["gptsovits_dir"]
    sys.path.insert(0, str(gptsovits_dir))

    from GPT_SoVITS.TTS_infer_pack.TTS import TTS, TTS_Config

    tts_config = TTS_Config(str(gptsovits_dir / "configs" / "tts_infer.yaml"))
    tts_config.sovits_path = str(ROOT / config["inference"]["sovits_model_path"])
    tts_config.gpt_path = str(ROOT / config["inference"]["gpt_model_path"])
    _ENGINE = TTS(tts_config)
    _CONFIG = config
    return _ENGINE, _CONFIG


def generate(text: str, ref_audio: str, ref_text: str, speed: float, top_k: int, temperature: float):
    if not text or not text.strip():
        return None, "請輸入文字。"

    try:
        tts, config = get_engine()
        infer = config["inference"]
        lang = config["speaker"]["language"]
        prompt_text = ref_text.strip() or read_reference_text(config)

        inputs = {
            "text": text.strip(),
            "text_lang": lang,
            "ref_audio_path": ref_audio,
            "prompt_text": prompt_text,
            "prompt_lang": lang,
            "top_k": int(top_k),
            "top_p": float(infer["top_p"]),
            "temperature": float(temperature),
            "text_split_method": infer.get("text_split_method", "cut5"),
            "batch_size": 1,
            "speed_factor": float(speed),
            "ref_text_free": not bool(prompt_text),
            "split_bucket": True,
        }

        chunks = []
        sample_rate = None
        for sample_rate, chunk in tts.run(inputs):
            chunks.append(chunk)
        if not chunks or sample_rate is None:
            return None, "沒有產生音訊。"

        audio = np.concatenate(chunks)
        output_dir = ROOT / config["paths"]["output_dir"]
        output_dir.mkdir(parents=True, exist_ok=True)
        out_path = output_dir / f"output_{dt.datetime.now().strftime('%Y%m%d_%H%M%S')}.wav"

        import soundfile as sf
        sf.write(str(out_path), audio, sample_rate)
        return (sample_rate, audio), f"完成：{out_path.name}"
    except Exception as exc:
        return None, f"錯誤：{exc}"


def create_ui():
    import gradio as gr

    config = load_config()
    refs = reference_choices(config)
    default_ref = str(ROOT / config["inference"]["reference_audio"])
    if default_ref not in refs and Path(default_ref).exists():
        refs.insert(0, default_ref)

    with gr.Blocks(title="Voice Clone Inference", theme=gr.themes.Soft()) as demo:
        gr.Markdown("# Voice Clone Inference")
        with gr.Row():
            with gr.Column(scale=3):
                text = gr.Textbox(label="文字", lines=8)
                button = gr.Button("生成", variant="primary")
                audio = gr.Audio(label="輸出", type="numpy")
                status = gr.Textbox(label="狀態", interactive=False)
            with gr.Column(scale=2):
                ref_audio = gr.Dropdown(choices=refs, value=default_ref if refs else None, label="Reference audio")
                ref_text = gr.Textbox(label="Reference text", value=read_reference_text(config), lines=3)
                speed = gr.Slider(0.6, 1.4, value=float(config["inference"]["speed_factor"]), step=0.05, label="Speed")
                top_k = gr.Slider(1, 20, value=int(config["inference"]["top_k"]), step=1, label="Top K")
                temperature = gr.Slider(0.2, 1.5, value=float(config["inference"]["temperature"]), step=0.05, label="Temperature")

        button.click(generate, [text, ref_audio, ref_text, speed, top_k, temperature], [audio, status])
    return demo


def main() -> None:
    demo = create_ui()
    demo.launch(server_name="127.0.0.1", server_port=7860, share=False, inbrowser=True)


if __name__ == "__main__":
    main()
