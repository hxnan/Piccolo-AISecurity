#!/usr/bin/env python3
"""Merge a PEFT LoRA adapter into the Piccolo-0.8B-VL base checkpoint.

The merged directory can be served by the same SGLang launch script and
re-evaluated with ``security/run_eval.py``.

Usage:
    python security/merge_adapter.py \
        --base /models/Piccolo-0.8B-VL \
        --adapter var/train/lora-v1/adapter \
        --out /models/Piccolo-0.8B-VL-lora-v1
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from pathlib import Path


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", required=True, type=Path)
    parser.add_argument("--adapter", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--device", default="cuda" if __import__("torch").cuda.is_available() else "cpu")
    args = parser.parse_args(argv)

    import torch
    from peft import PeftModel
    from transformers import AutoModelForImageTextToText, AutoProcessor, AutoTokenizer

    if not (args.base / "config.json").is_file():
        raise SystemExit(f"base checkpoint missing config.json: {args.base}")
    if not (args.adapter / "adapter_config.json").is_file():
        raise SystemExit(f"adapter missing adapter_config.json: {args.adapter}")
    if args.out.exists() and any(args.out.iterdir()):
        raise SystemExit(f"output directory is not empty: {args.out}")

    dtype = torch.bfloat16
    base = AutoModelForImageTextToText.from_pretrained(
        str(args.base), dtype=dtype, device_map={"": args.device}, local_files_only=True
    )
    merged = PeftModel.from_pretrained(base, str(args.adapter))
    merged = merged.merge_and_unload()
    merged.config.use_cache = False

    args.out.mkdir(parents=True, exist_ok=True)
    merged.save_pretrained(str(args.out), safe_serialization=True, max_shard_size="2GB")

    AutoTokenizer.from_pretrained(str(args.base), local_files_only=True).save_pretrained(str(args.out))
    try:
        AutoProcessor.from_pretrained(str(args.base), local_files_only=True).save_pretrained(str(args.out))
    except Exception as error:  # noqa: BLE001 - processor is optional for the text path
        print(f"processor copy skipped: {error}")

    for name in (
        "decision-inference.json",
        "chat_template.jinja",
        "generation_config.json",
        "processor_config.json",
        "preprocessor_config.json",
        "tokenizer_config.json",
        "special_tokens_map.json",
    ):
        source = args.base / name
        if source.is_file():
            shutil.copy2(source, args.out / name)

    weights = sorted(args.out.glob("*.safetensors"))
    if not weights:
        raise SystemExit("merge produced no safetensors weights")
    meta = {
        "base": str(args.base),
        "adapter": str(args.adapter),
        "out": str(args.out),
        "device": args.device,
        "weights": [
            {"path": path.name, "size": path.stat().st_size, "sha256": sha256(path)}
            for path in weights
        ],
    }
    (args.out / "merge.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n")
    print(f"merged: {args.out}")
    for item in meta["weights"]:
        print(f"  {item['path']} {item['size']} bytes {item['sha256'][:12]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
