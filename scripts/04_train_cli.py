#!/usr/bin/env python3
"""Best-effort GPT-SoVITS CLI training wrapper.

GPT-SoVITS changes its internal training scripts over time. This wrapper keeps
the common v2 layout working and fails with clear instructions when the local
GPT-SoVITS checkout uses a different interface.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT / "configs" / "voice_config.yaml"


def load_config() -> dict:
    with open(CONFIG_PATH, encoding="utf-8") as f:
        return yaml.safe_load(f)


def run(cmd: list[str], cwd: Path) -> None:
    print("\n$ " + " ".join(cmd))
    result = subprocess.run(cmd, cwd=str(cwd), check=False)
    if result.returncode != 0:
        raise SystemExit(f"Command failed with exit code {result.returncode}")


def first_existing(paths: list[Path]) -> Path | None:
    for path in paths:
        if path.exists():
            return path
    return None


def detect_layout(gptsovits_dir: Path) -> dict[str, Path]:
    base = gptsovits_dir / "GPT_SoVITS"
    return {
        "get_text": first_existing([base / "prepare_datasets" / "1-get-text.py", gptsovits_dir / "prepare_datasets" / "1-get-text.py"]),
        "get_hubert": first_existing([base / "prepare_datasets" / "2-get-hubert-wav32k.py", gptsovits_dir / "prepare_datasets" / "2-get-hubert-wav32k.py"]),
        "get_semantic": first_existing([base / "prepare_datasets" / "3-get-semantic.py", gptsovits_dir / "prepare_datasets" / "3-get-semantic.py"]),
        "s2_train": first_existing([base / "s2_train.py", gptsovits_dir / "s2_train.py"]),
        "s1_train": first_existing([base / "s1_train.py", gptsovits_dir / "s1_train.py"]),
        "s2_config": first_existing([base / "configs" / "s2.json", gptsovits_dir / "configs" / "s2.json"]),
    }


def require_layout(layout: dict[str, Path | None]) -> None:
    missing = [key for key, value in layout.items() if value is None]
    if missing:
        print("This GPT-SoVITS checkout does not match the supported CLI layout.")
        print("Missing: " + ", ".join(missing))
        print("Use scripts\\04_launch_training.bat and train from GPT-SoVITS WebUI instead.")
        raise SystemExit(1)


def pretrained_dir(gptsovits_dir: Path, name: str) -> str:
    candidates = [
        gptsovits_dir / "GPT_SoVITS" / "pretrained_models" / name,
        gptsovits_dir / "pretrained_models" / name,
    ]
    found = first_existing(candidates)
    return str(found or candidates[0])


def patch_s2_config(template: Path, output: Path, logs_dir: Path, train_cfg: dict) -> None:
    with open(template, encoding="utf-8") as f:
        cfg = json.load(f)

    if "train" in cfg:
        cfg["train"]["batch_size"] = int(train_cfg["batch_size"])
        cfg["train"]["epochs"] = int(train_cfg["sovits_epochs"])
        cfg["train"]["save_every_epoch"] = int(train_cfg["save_every_epoch"])
        if "exp_dir" in cfg["train"]:
            cfg["train"]["exp_dir"] = str(logs_dir)

    if "data" in cfg:
        for key in ["training_files", "validation_files"]:
            if key in cfg["data"]:
                cfg["data"][key] = str(logs_dir / "6-name2semantic.tsv")

    output.parent.mkdir(parents=True, exist_ok=True)
    with open(output, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)


def copy_latest_models(logs_dir: Path, models_dir: Path) -> None:
    models_dir.mkdir(parents=True, exist_ok=True)
    pths = sorted(logs_dir.glob("*.pth"), key=lambda p: p.stat().st_mtime, reverse=True)
    ckpts = sorted(logs_dir.glob("*.ckpt"), key=lambda p: p.stat().st_mtime, reverse=True)

    if pths:
        shutil.copy2(pths[0], models_dir / "sovits_model.pth")
        print(f"Copied {pths[0].name} -> models/sovits_model.pth")
    else:
        print("No .pth model found in logs.")

    if ckpts:
        shutil.copy2(ckpts[0], models_dir / "gpt_model.ckpt")
        print(f"Copied {ckpts[0].name} -> models/gpt_model.ckpt")
    else:
        print("No .ckpt model found in logs.")


def parse_args() -> argparse.Namespace:
    config = load_config()
    train_cfg = config["training"]
    parser = argparse.ArgumentParser(description="Train GPT-SoVITS from validated dataset.")
    parser.add_argument("--dataset", required=True)
    parser.add_argument("--wav_dir", required=True)
    parser.add_argument("--gptsovits_dir", default=str(ROOT / config["paths"]["gptsovits_dir"]))
    parser.add_argument("--exp_name", default=train_cfg["exp_name"])
    parser.add_argument("--skip_prepare", action="store_true")
    parser.add_argument("--skip_sovits", action="store_true")
    parser.add_argument("--skip_gpt", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config = load_config()
    train_cfg = config["training"]
    dataset = Path(args.dataset).resolve()
    wav_dir = Path(args.wav_dir).resolve()
    gptsovits_dir = Path(args.gptsovits_dir).resolve()
    logs_root = gptsovits_dir / "logs"
    logs_dir = logs_root / args.exp_name

    if not dataset.exists():
        raise SystemExit(f"Dataset not found: {dataset}")
    if not wav_dir.exists():
        raise SystemExit(f"Wav dir not found: {wav_dir}")
    if not gptsovits_dir.exists():
        raise SystemExit(f"GPT-SoVITS not found: {gptsovits_dir}")

    layout = detect_layout(gptsovits_dir)
    require_layout(layout)

    print("GPT-SoVITS CLI training")
    print(f"Experiment: {args.exp_name}")
    print(f"Dataset:    {dataset}")
    print(f"Wav dir:    {wav_dir}")
    print(f"Logs:       {logs_dir}")

    py = sys.executable
    bert = pretrained_dir(gptsovits_dir, "chinese-roberta-wwm-ext-large")
    cnhubert = pretrained_dir(gptsovits_dir, "chinese-hubert-base")

    if not args.skip_prepare:
        logs_dir.mkdir(parents=True, exist_ok=True)
        run([
            py, str(layout["get_text"]),
            "--inp_text", str(dataset),
            "--inp_wav_dir", str(wav_dir),
            "--exp_name", args.exp_name,
            "--opt_dir", str(logs_root),
            "--bert_pretrained_dir", bert,
            "--cnhubert_base_dir", cnhubert,
        ], gptsovits_dir)
        run([
            py, str(layout["get_hubert"]),
            "--inp_text", str(dataset),
            "--exp_name", args.exp_name,
            "--opt_dir", str(logs_root),
            "--cnhubert_base_dir", cnhubert,
        ], gptsovits_dir)
        run([
            py, str(layout["get_semantic"]),
            "--exp_name", args.exp_name,
            "--opt_dir", str(logs_root),
            "--s2config_path", str(layout["s2_config"]),
        ], gptsovits_dir)

    if not args.skip_sovits:
        s2_config = logs_dir / "s2.json"
        patch_s2_config(layout["s2_config"], s2_config, logs_dir, train_cfg)
        run([py, str(layout["s2_train"]), "--config", str(s2_config)], gptsovits_dir)

    if not args.skip_gpt:
        run([
            py, str(layout["s1_train"]),
            "--exp_root", str(logs_root),
            "--exp_name", args.exp_name,
            "--batch_size", str(train_cfg["batch_size"]),
            "--total_epoch", str(train_cfg["gpt_epochs"]),
            "--save_every_epoch", str(train_cfg["save_every_epoch"]),
        ], gptsovits_dir)

    copy_latest_models(logs_dir, ROOT / config["paths"]["models_dir"])
    print("Training wrapper finished.")


if __name__ == "__main__":
    main()
