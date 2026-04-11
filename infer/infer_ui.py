#!/usr/bin/env python3
"""
推論 Web UI：本地瀏覽器操作介面
執行: python infer/infer_ui.py
瀏覽器開啟: http://localhost:7860
"""

import sys
import yaml
import datetime
import numpy as np
from pathlib import Path

ROOT = Path(__file__).parent.parent
GPT_SOVITS_DIR = ROOT / "GPT-SoVITS"
if GPT_SOVITS_DIR.exists():
    sys.path.insert(0, str(GPT_SOVITS_DIR))


def load_config():
    config_path = ROOT / "configs" / "voice_config.yaml"
    with open(config_path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def get_reference_audios() -> list[str]:
    """取得可用的參考音訊清單"""
    ref_dir = ROOT / "data" / "reference"
    sliced_dir = ROOT / "data" / "sliced"
    refs = []

    if ref_dir.exists():
        refs.extend([str(p) for p in ref_dir.glob("*.wav")])

    # 也可從切段中選（取前 20 個方便選擇）
    if sliced_dir.exists():
        sliced = sorted(sliced_dir.glob("*.wav"))[:20]
        refs.extend([str(p) for p in sliced])

    return refs if refs else ["（無可用參考音訊）"]


def load_tts_engine(config: dict):
    """載入 TTS 引擎"""
    try:
        from GPT_SoVITS.TTS_infer_pack.TTS import TTS, TTS_Config
    except ImportError:
        raise RuntimeError(
            "無法匯入 GPT-SoVITS\n"
            f"請確認 {GPT_SOVITS_DIR} 存在且已安裝相依套件"
        )

    sovits_path = str(ROOT / config["inference"]["sovits_model_path"])
    gpt_path = str(ROOT / config["inference"]["gpt_model_path"])

    tts_config = TTS_Config(str(GPT_SOVITS_DIR / "configs" / "tts_infer.yaml"))
    tts_config.sovits_path = sovits_path
    tts_config.gpt_path = gpt_path

    return TTS(tts_config)


# ── 全域 TTS 引擎（避免重複載入）─────────────────────
_tts_engine = None
_config = None


def get_tts_engine():
    global _tts_engine, _config
    if _tts_engine is None:
        _config = load_config()
        _tts_engine = load_tts_engine(_config)
    return _tts_engine, _config


def generate(
    text: str,
    ref_audio_path: str,
    ref_text: str,
    speed: float,
    top_k: int,
    temperature: float,
):
    """Gradio 生成函數"""
    import soundfile as sf
    import tempfile
    import os

    if not text or not text.strip():
        return None, "❌ 請輸入要合成的文字"

    try:
        tts, config = get_tts_engine()
        lang = config["speaker"]["language"]

        inputs = {
            "text": text.strip(),
            "text_lang": lang,
            "ref_audio_path": ref_audio_path,
            "prompt_text": ref_text.strip() if ref_text else "",
            "prompt_lang": lang,
            "top_k": int(top_k),
            "top_p": 1.0,
            "temperature": float(temperature),
            "text_split_method": "cut5",
            "batch_size": 1,
            "speed_factor": float(speed),
            "ref_text_free": not bool(ref_text and ref_text.strip()),
            "split_bucket": True,
        }

        audio_chunks = []
        sample_rate = None
        for sr, chunk in tts.run(inputs):
            sample_rate = sr
            audio_chunks.append(chunk)

        if not audio_chunks:
            return None, "❌ 生成失敗：未產生音訊"

        audio = np.concatenate(audio_chunks)
        duration = len(audio) / sample_rate

        # 同時存到 output 資料夾
        output_dir = ROOT / config["inference"]["output_dir"]
        output_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        saved_path = output_dir / f"output_{timestamp}.wav"
        sf.write(str(saved_path), audio, sample_rate)

        status = f"✅ 生成完成！時長 {duration:.1f} 秒 | 已存至 {saved_path.name}"
        return (sample_rate, audio), status

    except Exception as e:
        import traceback
        return None, f"❌ 錯誤: {str(e)}\n\n{traceback.format_exc()}"


def batch_generate(text_input: str, ref_audio_path: str, ref_text: str, speed: float):
    """批次生成（多段文字）"""
    lines = [line.strip() for line in text_input.strip().split("\n") if line.strip()]
    if not lines:
        return "❌ 請輸入文字"

    results = []
    for i, line in enumerate(lines, start=1):
        audio, status = generate(line, ref_audio_path, ref_text, speed, 5, 1.0)
        if "✅" in status:
            results.append(f"✅ [{i}] {line[:30]}... 完成")
        else:
            results.append(f"❌ [{i}] {line[:30]}... 失敗")

    return "\n".join(results)


def create_ui():
    import gradio as gr

    config = load_config()
    ref_audios = get_reference_audios()
    default_ref = str(ROOT / config["inference"]["reference_audio"]) \
        if (ROOT / config["inference"]["reference_audio"]).exists() \
        else (ref_audios[0] if ref_audios else "")

    with gr.Blocks(
        title="AI 聲音克隆",
        theme=gr.themes.Soft(),
        css="""
        .main-header { text-align: center; padding: 20px 0; }
        .status-box { font-family: monospace; }
        """
    ) as demo:

        gr.HTML("""
        <div class="main-header">
            <h1>🎙️ AI 聲音克隆</h1>
            <p>輸入文案，用你的聲音朗讀出來</p>
        </div>
        """)

        with gr.Tab("🎤 單段生成"):
            with gr.Row():
                with gr.Column(scale=3):
                    text_input = gr.Textbox(
                        label="📝 輸入文案",
                        placeholder="在這裡輸入你想用自己聲音說的話...",
                        lines=6,
                        max_lines=20,
                    )
                    generate_btn = gr.Button("🎵 生成音訊", variant="primary", size="lg")

                with gr.Column(scale=2):
                    gr.Markdown("### ⚙️ 參考音訊設定")
                    ref_audio = gr.Dropdown(
                        choices=ref_audios,
                        value=default_ref,
                        label="參考音訊（選一段你的聲音）",
                        interactive=True,
                    )
                    ref_text_input = gr.Textbox(
                        label="參考音訊內容（選填，填入後品質更好）",
                        placeholder="參考音訊裡說的話...",
                        value=config["inference"].get("reference_text", ""),
                        lines=2,
                    )

                    gr.Markdown("### 🎛️ 生成參數")
                    speed_slider = gr.Slider(
                        minimum=0.5, maximum=2.0, value=1.0, step=0.05,
                        label="語速（1.0=正常）",
                    )
                    top_k_slider = gr.Slider(
                        minimum=1, maximum=20, value=5, step=1,
                        label="Top-K（越低越穩定）",
                    )
                    temperature_slider = gr.Slider(
                        minimum=0.1, maximum=2.0, value=1.0, step=0.05,
                        label="溫度（越低越穩定）",
                    )

            with gr.Row():
                audio_output = gr.Audio(label="🔊 生成結果", type="numpy")
                status_text = gr.Textbox(
                    label="狀態",
                    interactive=False,
                    elem_classes=["status-box"],
                )

            generate_btn.click(
                fn=generate,
                inputs=[text_input, ref_audio, ref_text_input, speed_slider, top_k_slider, temperature_slider],
                outputs=[audio_output, status_text],
            )

        with gr.Tab("📋 批次生成"):
            gr.Markdown("""
            ### 批次生成
            每行一條文案，系統會依序生成並存到 `output/` 資料夾
            """)

            with gr.Row():
                with gr.Column():
                    batch_text = gr.Textbox(
                        label="📝 批次文案（每行一條）",
                        placeholder="大家好，歡迎收聽今天的節目\n今天我們要聊的主題是...\n...",
                        lines=15,
                    )
                    batch_ref_audio = gr.Dropdown(
                        choices=ref_audios,
                        value=default_ref,
                        label="參考音訊",
                    )
                    batch_ref_text = gr.Textbox(
                        label="參考音訊內容",
                        lines=2,
                    )
                    batch_speed = gr.Slider(0.5, 2.0, value=1.0, step=0.05, label="語速")
                    batch_btn = gr.Button("🚀 開始批次生成", variant="primary")

                with gr.Column():
                    batch_status = gr.Textbox(
                        label="生成進度",
                        lines=20,
                        interactive=False,
                    )

            batch_btn.click(
                fn=batch_generate,
                inputs=[batch_text, batch_ref_audio, batch_ref_text, batch_speed],
                outputs=[batch_status],
            )

        with gr.Tab("ℹ️ 使用說明"):
            gr.Markdown(f"""
## 使用說明

### 🎯 基本流程
1. 在「參考音訊」選一段清晰的你的聲音（3~10 秒）
2. 在「參考音訊內容」輸入那段音訊說的話（選填但建議填）
3. 在文案輸入框輸入想合成的文字
4. 點擊「生成音訊」

### 💡 提升品質技巧
- 參考音訊選**情緒和語速接近目標**的片段
- 填寫參考音訊內容可明顯提升準確率
- 長文建議使用「批次生成」分段處理
- 語速建議 0.85~1.1 之間（自然範圍）

### 📁 輸出位置
所有生成的音訊自動存到：
`{ROOT / config['inference']['output_dir']}`

### ⚙️ 目前設定
- 說話人: `{config['speaker']['name']}`
- 語言: `{config['speaker']['language']}`
- SoVITS 模型: `{config['inference']['sovits_model_path']}`
- GPT 模型: `{config['inference']['gpt_model_path']}`
            """)

    return demo


def main():
    try:
        import gradio as gr
    except ImportError:
        print("找不到 gradio，正在安裝...")
        import subprocess
        subprocess.run([sys.executable, "-m", "pip", "install", "gradio>=4.0.0"])
        import gradio as gr

    print("\n" + "="*45)
    print("  AI 聲音克隆 — Web UI 啟動中")
    print("="*45)
    print(f"\n  瀏覽器開啟: http://localhost:7860\n")

    demo = create_ui()
    demo.launch(
        server_name="127.0.0.1",
        server_port=7860,
        share=False,
        inbrowser=True,
    )


if __name__ == "__main__":
    main()
