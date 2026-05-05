#!/usr/bin/env python3
"""
Step 4 CLI 版：不需要 WebUI，直接執行 GPT-SoVITS 訓練
等同於 WebUI 的：
  1A. 一鍵三連（格式化資料集）
  1B. SoVITS 訓練
  1C. GPT 訓練
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

# 讀取 voice_config.yaml（如果存在）
def load_voice_config() -> dict:
    config_path = Path(__file__).parent.parent / "configs" / "voice_config.yaml"
    if not config_path.exists():
        return {}
    try:
        import yaml
        with open(config_path, encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    except Exception:
        return {}

# ── 顏色輸出 ──────────────────────────────────────────────
try:
    from colorama import Fore, Style, init
    init()
    def ok(msg):   print(f"{Fore.GREEN}[OK] {msg}{Style.RESET_ALL}")
    def err(msg):  print(f"{Fore.RED}[錯誤] {msg}{Style.RESET_ALL}")
    def info(msg): print(f"{Fore.CYAN}[>>] {msg}{Style.RESET_ALL}")
    def warn(msg): print(f"{Fore.YELLOW}[警告] {msg}{Style.RESET_ALL}")
except ImportError:
    def ok(msg):   print(f"[OK] {msg}")
    def err(msg):  print(f"[錯誤] {msg}")
    def info(msg): print(f"[>>] {msg}")
    def warn(msg): print(f"[警告] {msg}")


def run(cmd: list, cwd: Path = None, desc: str = "") -> bool:
    """執行命令，即時顯示輸出，回傳是否成功"""
    if desc:
        info(desc)
    print(f"    命令: {' '.join(str(c) for c in cmd)}\n")

    result = subprocess.run(
        cmd,
        cwd=str(cwd) if cwd else None,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if result.returncode != 0:
        err(f"命令失敗（返回碼 {result.returncode}）")
        return False
    return True


def detect_gptsovits_structure(gptsovits_dir: Path) -> dict:
    """
    偵測 GPT-SoVITS 的目錄結構，相容新舊版本。
    回傳各腳本的實際路徑。
    """
    # 嘗試不同的路徑組合（不同版本結構不同）
    candidates = {
        "get_text": [
            gptsovits_dir / "GPT_SoVITS" / "prepare_datasets" / "1-get-text.py",
            gptsovits_dir / "prepare_datasets" / "1-get-text.py",
        ],
        "get_hubert": [
            gptsovits_dir / "GPT_SoVITS" / "prepare_datasets" / "2-get-hubert-wav32k.py",
            gptsovits_dir / "prepare_datasets" / "2-get-hubert-wav32k.py",
        ],
        "get_semantic": [
            gptsovits_dir / "GPT_SoVITS" / "prepare_datasets" / "3-get-semantic.py",
            gptsovits_dir / "prepare_datasets" / "3-get-semantic.py",
        ],
        "s2_train": [
            gptsovits_dir / "GPT_SoVITS" / "s2_train.py",
            gptsovits_dir / "s2_train.py",
        ],
        "s1_train": [
            gptsovits_dir / "GPT_SoVITS" / "s1_train.py",
            gptsovits_dir / "s1_train.py",
        ],
        "s2_config": [
            gptsovits_dir / "GPT_SoVITS" / "configs" / "s2.json",
            gptsovits_dir / "configs" / "s2.json",
        ],
        "s1_config": [
            gptsovits_dir / "GPT_SoVITS" / "configs" / "s1longer.yaml",
            gptsovits_dir / "configs" / "s1longer.yaml",
            gptsovits_dir / "GPT_SoVITS" / "configs" / "s1.yaml",
            gptsovits_dir / "configs" / "s1.yaml",
        ],
    }

    found = {}
    for key, paths in candidates.items():
        for p in paths:
            if p.exists():
                found[key] = p
                break

    return found


def find_pretrained_models(gptsovits_dir: Path) -> dict:
    """找到預訓練模型路徑（GPT-SoVITS 安裝時附帶的底模）"""
    models = {}

    # GPT-SoVITS 預訓練模型通常在這些位置
    bert_candidates = [
        gptsovits_dir / "GPT_SoVITS" / "pretrained_models" / "chinese-roberta-wwm-ext-large",
        gptsovits_dir / "pretrained_models" / "chinese-roberta-wwm-ext-large",
        gptsovits_dir / "GPT_SoVITS" / "text" / "chinese-roberta-wwm-ext-large",
    ]
    cnhubert_candidates = [
        gptsovits_dir / "GPT_SoVITS" / "pretrained_models" / "chinese-hubert-base",
        gptsovits_dir / "pretrained_models" / "chinese-hubert-base",
    ]
    ssl_candidates = [
        gptsovits_dir / "GPT_SoVITS" / "pretrained_models" / "chinese-hubert-base",
        gptsovits_dir / "pretrained_models" / "chinese-hubert-base",
    ]

    for p in bert_candidates:
        if p.exists():
            models["bert"] = p
            break
    for p in cnhubert_candidates:
        if p.exists():
            models["cnhubert"] = p
            break

    return models


def patch_s2_config(template_path: Path, output_path: Path, exp_name: str,
                    gptsovits_dir: Path, batch_size: int, epochs: int,
                    save_every: int) -> bool:
    """修改 SoVITS 訓練設定檔"""
    try:
        with open(template_path, encoding="utf-8") as f:
            cfg = json.load(f)

        logs_dir = gptsovits_dir / "logs" / exp_name

        # 更新路徑與參數
        if "train" in cfg:
            cfg["train"]["batch_size"] = batch_size
            cfg["train"]["epochs"] = epochs
            cfg["train"]["save_every_epoch"] = save_every
            if "exp_dir" in cfg["train"]:
                cfg["train"]["exp_dir"] = str(logs_dir)

        if "data" in cfg:
            for key in ["training_files", "validation_files"]:
                if key in cfg["data"]:
                    cfg["data"][key] = str(logs_dir / "6-name2semantic.tsv")

        # s2config 路徑
        for section in cfg.values():
            if isinstance(section, dict):
                for k, v in section.items():
                    if isinstance(v, str) and "exp_dir" in k:
                        section[k] = str(logs_dir)

        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)

        ok(f"SoVITS 設定已寫入: {output_path}")
        return True
    except Exception as e:
        err(f"修改 SoVITS 設定失敗: {e}")
        return False


def step1a_format_dataset(scripts: dict, gptsovits_dir: Path,
                           dataset_list: Path, wav_dir: Path,
                           exp_name: str, python_exe: str) -> bool:
    """
    1A. 格式化資料集（等同 WebUI 的「一鍵三連」）
    依序執行三個前處理腳本
    """
    logs_dir = gptsovits_dir / "logs" / exp_name
    logs_dir.mkdir(parents=True, exist_ok=True)

    pretrained = find_pretrained_models(gptsovits_dir)
    bert_dir = str(pretrained.get("bert", gptsovits_dir / "GPT_SoVITS" / "pretrained_models" / "chinese-roberta-wwm-ext-large"))
    cnhubert_dir = str(pretrained.get("cnhubert", gptsovits_dir / "GPT_SoVITS" / "pretrained_models" / "chinese-hubert-base"))

    # ── 1Aa: 文本獲取 ──────────────────────────────────────
    if "get_text" not in scripts:
        err("找不到 1-get-text.py")
        return False

    print("\n" + "="*50)
    info("1Aa / 文本特徵提取（get-text）")
    print("="*50)
    ok_flag = run(
        [python_exe, str(scripts["get_text"]),
         "--inp_text", str(dataset_list),
         "--inp_wav_dir", str(wav_dir),
         "--exp_name", exp_name,
         "--opt_dir", str(gptsovits_dir / "logs"),
         "--bert_pretrained_dir", bert_dir,
         "--cnhubert_base_dir", cnhubert_dir],
        cwd=gptsovits_dir,
        desc="提取 BERT 文字特徵..."
    )
    if not ok_flag:
        return False
    ok("1Aa 完成：2-name2text.txt + 3-bert/")

    # ── 1Ab: SSL 特徵（HuBERT + wav32k） ──────────────────
    if "get_hubert" not in scripts:
        err("找不到 2-get-hubert-wav32k.py")
        return False

    print("\n" + "="*50)
    info("1Ab / SSL 特徵提取（hubert + wav32k）")
    print("="*50)
    ok_flag = run(
        [python_exe, str(scripts["get_hubert"]),
         "--inp_text", str(dataset_list),
         "--exp_name", exp_name,
         "--opt_dir", str(gptsovits_dir / "logs"),
         "--cnhubert_base_dir", cnhubert_dir],
        cwd=gptsovits_dir,
        desc="提取 HuBERT 特徵 + 轉為 32kHz WAV..."
    )
    if not ok_flag:
        return False
    ok("1Ab 完成：4-cnhubert/ + 5-wav32k/")

    # ── 1Ac: 語義特徵 ──────────────────────────────────────
    if "get_semantic" not in scripts:
        err("找不到 3-get-semantic.py")
        return False

    # 找 s2config 路徑
    s2config = scripts.get("s2_config", gptsovits_dir / "GPT_SoVITS" / "configs" / "s2.json")

    print("\n" + "="*50)
    info("1Ac / 語義特徵提取（semantic tokens）")
    print("="*50)
    ok_flag = run(
        [python_exe, str(scripts["get_semantic"]),
         "--exp_name", exp_name,
         "--opt_dir", str(gptsovits_dir / "logs"),
         "--s2config_path", str(s2config)],
        cwd=gptsovits_dir,
        desc="提取語義特徵..."
    )
    if not ok_flag:
        return False
    ok("1Ac 完成：6-name2semantic.tsv")
    return True


def step1b_train_sovits(scripts: dict, gptsovits_dir: Path,
                         exp_name: str, batch_size: int, epochs: int,
                         save_every: int, python_exe: str) -> bool:
    """1B. 訓練 SoVITS 模型"""
    if "s2_train" not in scripts:
        err("找不到 s2_train.py")
        return False

    print("\n" + "="*50)
    info("1B / SoVITS 模型訓練")
    print("="*50)

    # 生成訓練設定
    s2_template = scripts.get("s2_config")
    if not s2_template:
        err("找不到 s2.json 設定範本")
        return False

    s2_config_out = gptsovits_dir / "logs" / exp_name / "s2.json"
    if not patch_s2_config(s2_template, s2_config_out, exp_name,
                           gptsovits_dir, batch_size, epochs, save_every):
        return False

    ok_flag = run(
        [python_exe, str(scripts["s2_train"]),
         "--config", str(s2_config_out)],
        cwd=gptsovits_dir,
        desc=f"訓練 SoVITS（{epochs} epochs, batch={batch_size}）..."
    )
    if not ok_flag:
        return False
    ok(f"SoVITS 訓練完成 → {gptsovits_dir}/logs/{exp_name}/*.pth")
    return True


def step1c_train_gpt(scripts: dict, gptsovits_dir: Path,
                      exp_name: str, batch_size: int, epochs: int,
                      python_exe: str) -> bool:
    """1C. 訓練 GPT 模型"""
    if "s1_train" not in scripts:
        err("找不到 s1_train.py")
        return False

    print("\n" + "="*50)
    info("1C / GPT 語言模型訓練")
    print("="*50)

    logs_dir = gptsovits_dir / "logs" / exp_name

    # GPT 訓練可用命令列參數直接傳入
    ok_flag = run(
        [python_exe, str(scripts["s1_train"]),
         "--exp_root", str(gptsovits_dir / "logs"),
         "--exp_name", exp_name,
         "--batch_size", str(batch_size),
         "--total_epoch", str(epochs),
         "--save_every_epoch", "5"],
        cwd=gptsovits_dir,
        desc=f"訓練 GPT 模型（{epochs} epochs）..."
    )
    if not ok_flag:
        return False
    ok(f"GPT 訓練完成 → {logs_dir}/*.ckpt")
    return True


def copy_models_to_output(gptsovits_dir: Path, exp_name: str,
                           models_dir: Path) -> None:
    """把訓練好的模型複製到 models/ 資料夾"""
    logs_dir = gptsovits_dir / "logs" / exp_name
    models_dir.mkdir(parents=True, exist_ok=True)

    copied = []

    # 找最新的 SoVITS (.pth)
    pth_files = sorted(logs_dir.glob("*.pth"), key=lambda x: x.stat().st_mtime, reverse=True)
    if pth_files:
        dst = models_dir / "sovits_model.pth"
        shutil.copy2(pth_files[0], dst)
        copied.append(f"SoVITS: {dst}")

    # 找最新的 GPT (.ckpt)
    ckpt_files = sorted(logs_dir.glob("*.ckpt"), key=lambda x: x.stat().st_mtime, reverse=True)
    if ckpt_files:
        dst = models_dir / "gpt_model.ckpt"
        shutil.copy2(ckpt_files[0], dst)
        copied.append(f"GPT: {dst}")

    if copied:
        print()
        ok("模型已自動複製到 models/ 資料夾：")
        for c in copied:
            print(f"   {c}")
    else:
        warn(f"未找到模型檔案，請手動從 {logs_dir} 複製到 models/")


def main():
    # 從 voice_config.yaml 取預設值
    cfg = load_voice_config()
    train_cfg = cfg.get("training", {})

    parser = argparse.ArgumentParser(description="GPT-SoVITS CLI 訓練（無 WebUI）")
    parser.add_argument("--dataset",      required=True,  help="訓練清單路徑（dataset_validated.txt）")
    parser.add_argument("--wav_dir",      required=True,  help="切段音訊資料夾")
    parser.add_argument("--exp_name",     default=cfg.get("speaker", {}).get("name", "my_voice"),
                        help="實驗名稱")
    parser.add_argument("--gptsovits_dir",required=True,  help="GPT-SoVITS 資料夾路徑")
    parser.add_argument("--sovits_epochs",type=int,
                        default=train_cfg.get("sovits_epochs", 8),
                        help="SoVITS 訓練輪數")
    parser.add_argument("--gpt_epochs",   type=int,
                        default=train_cfg.get("gpt_epochs", 15),
                        help="GPT 訓練輪數")
    parser.add_argument("--batch_size",   type=int,
                        default=train_cfg.get("batch_size", 4),
                        help="Batch size（VRAM<8GB 用 2）")
    parser.add_argument("--save_every",   type=int,
                        default=train_cfg.get("save_every_epoch", 4),
                        help="每幾輪存一次")
    parser.add_argument("--skip_format",  action="store_true",  help="跳過 1A 資料格式化（已做過）")
    parser.add_argument("--skip_sovits",  action="store_true",  help="只訓練 GPT，跳過 SoVITS")
    parser.add_argument("--skip_gpt",     action="store_true",  help="只訓練 SoVITS，跳過 GPT")
    args = parser.parse_args()

    # ── 路徑轉換 ──────────────────────────────────────────
    dataset_list  = Path(args.dataset).resolve()
    wav_dir       = Path(args.wav_dir).resolve()
    gptsovits_dir = Path(args.gptsovits_dir).resolve()
    project_root  = Path(__file__).parent.parent
    models_dir    = project_root / "models"

    python_exe = sys.executable

    print(f"\n{'='*55}")
    print("  GPT-SoVITS CLI 訓練工具")
    print(f"{'='*55}")
    print(f"  實驗名稱 : {args.exp_name}")
    print(f"  訓練資料 : {dataset_list}")
    print(f"  音訊資料夾: {wav_dir}")
    print(f"  SoVITS   : {args.sovits_epochs} epochs")
    print(f"  GPT      : {args.gpt_epochs} epochs")
    print(f"  Batch    : {args.batch_size}")
    print(f"{'='*55}\n")

    # ── 前置檢查 ──────────────────────────────────────────
    if not dataset_list.exists():
        err(f"找不到訓練清單: {dataset_list}")
        sys.exit(1)

    if not wav_dir.exists():
        err(f"找不到音訊資料夾: {wav_dir}")
        sys.exit(1)

    if not gptsovits_dir.exists():
        err(f"找不到 GPT-SoVITS: {gptsovits_dir}")
        err("請先執行 setup\\install.bat")
        sys.exit(1)

    # ── 偵測腳本路徑 ──────────────────────────────────────
    scripts = detect_gptsovits_structure(gptsovits_dir)

    missing = []
    required = ["get_text", "get_hubert", "get_semantic", "s2_train", "s1_train", "s2_config"]
    for key in required:
        if key not in scripts:
            missing.append(key)

    if missing:
        err("GPT-SoVITS 結構異常，找不到以下腳本：")
        for m in missing:
            print(f"   缺少: {m}")
        print()
        info("嘗試列出 GPT-SoVITS 目錄結構以供診斷：")
        for p in sorted(gptsovits_dir.rglob("*.py"))[:20]:
            print(f"   {p.relative_to(gptsovits_dir)}")
        sys.exit(1)

    ok("GPT-SoVITS 腳本偵測完成：")
    for k, v in scripts.items():
        print(f"   {k}: {v.relative_to(gptsovits_dir)}")
    print()

    # ── 執行訓練流程 ───────────────────────────────────────
    if not args.skip_format:
        info("開始 Step 1A：格式化資料集（一鍵三連）")
        if not step1a_format_dataset(scripts, gptsovits_dir, dataset_list,
                                      wav_dir, args.exp_name, python_exe):
            err("資料集格式化失敗，停止訓練")
            sys.exit(1)
        ok("Step 1A 完成！\n")
    else:
        warn("已跳過 1A 資料格式化")

    if not args.skip_sovits:
        info("開始 Step 1B：SoVITS 訓練")
        if not step1b_train_sovits(scripts, gptsovits_dir, args.exp_name,
                                    args.batch_size, args.sovits_epochs,
                                    args.save_every, python_exe):
            err("SoVITS 訓練失敗")
            sys.exit(1)
        ok("Step 1B 完成！\n")
    else:
        warn("已跳過 SoVITS 訓練")

    if not args.skip_gpt:
        info("開始 Step 1C：GPT 訓練")
        if not step1c_train_gpt(scripts, gptsovits_dir, args.exp_name,
                                  args.batch_size, args.gpt_epochs, python_exe):
            err("GPT 訓練失敗")
            sys.exit(1)
        ok("Step 1C 完成！\n")
    else:
        warn("已跳過 GPT 訓練")

    # ── 自動複製模型 ───────────────────────────────────────
    copy_models_to_output(gptsovits_dir, args.exp_name, models_dir)

    print(f"\n{'='*55}")
    ok("全部訓練完成！")
    print(f"{'='*55}")
    print(f"\n下一步: python infer/infer_cli.py --text \"測試文字\"")
    print()


if __name__ == "__main__":
    main()
