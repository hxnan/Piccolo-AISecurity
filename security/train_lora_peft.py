#!/usr/bin/env python3
"""PEFT LoRA trainer for Piccolo-0.8B-VL on the AISecurity decision interface.

This is not a generic causal-LM SFT script. It reproduces the inference
contract used by ``/v1/systemone``:

* build prompts with the FlexDM ``flex_twice`` layout;
* make every full-attention layer bidirectional;
* read logits only for the candidate tokens at the answer position;
* optimise cross-entropy over those candidate logits.

The v1 data is short (p95 ~900 characters), so the default batch is 1 with
gradient accumulation. Batching with padding is intentionally not enabled:
any padding bug would silently change the attention semantics.

Usage:
    python security/train_lora_peft.py \
        --model /models/Piccolo-0.8B-VL \
        --train security/training/ais_security_train_v1.jsonl \
        --out var/train/lora-v1 \
        --epochs 3 --grad-accum 16

Smoke on the GPU host first:
    python security/train_lora_peft.py ... --max-steps 20
"""
from __future__ import annotations

import argparse
import json
import math
import os
import random
import sys
import time
from pathlib import Path
from types import SimpleNamespace

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT / "inference" / "reference"))

from piccolo_inference import FlexCompiler  # noqa: E402
from piccolo_layout import Layout, render_question  # noqa: E402

DEFAULT_TARGETS = (
    "q_proj,k_proj,v_proj,o_proj,gate_proj,up_proj,down_proj,"
    "in_proj_qkv,in_proj_z,in_proj_b,in_proj_a,out_proj"
)


def read_jsonl(path: Path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def candidate_target(row, qtype: str, value) -> int:
    keys = list(row.option_keys)
    if qtype == "noul":
        wanted = bool(value) if isinstance(value, bool) else str(value).lower() == "yes"
        for candidate in (wanted, "yes" if wanted else "no", 1 if wanted else 0):
            if candidate in keys:
                return keys.index(candidate)
        raise ValueError(f"cannot map noul label {value!r} to {keys!r}")
    if qtype == "score":
        wanted = str(int(value))
    else:
        wanted = str(value)
    if wanted not in [str(k) for k in keys]:
        raise ValueError(f"label {wanted!r} not in {keys!r}")
    return [str(k) for k in keys].index(wanted)


def build_samples(path: Path, tokenizer, max_seq_len: int, split: str, limit=None):
    compiler = FlexCompiler(
        tokenizer,
        SimpleNamespace(Layout=Layout, render_question=render_question),
        max_context=max(max_seq_len, 4096),
        twice_max_tokens=3000,
    )
    rows = read_jsonl(path)
    samples = []
    skipped = []
    for record in rows:
        if record.get("split") != split:
            continue
        for qid, question in record["questions"].items():
            try:
                compiled, _ = compiler.compile({"state": record["state"], "questions": {qid: question}})
            except Exception as error:  # noqa: BLE001 - data diagnostics
                skipped.append((record["id"], qid, f"compile: {error}"))
                continue
            for row in compiled:
                if len(row.input_ids) > max_seq_len:
                    skipped.append((record["id"], qid, f"tokens {len(row.input_ids)} > {max_seq_len}"))
                    continue
                try:
                    target = candidate_target(row, question["type"], record["labels"][qid]["value"])
                except (KeyError, TypeError, ValueError) as error:
                    skipped.append((record["id"], qid, f"target: {error}"))
                    continue
                samples.append(
                    {
                        "record_id": record["id"],
                        "question_id": qid,
                        "category": record["category"],
                        "input_ids": list(row.input_ids),
                        "candidate_ids": list(row.candidate_ids),
                        "target": target,
                    }
                )
                if limit and len(samples) >= limit:
                    return samples, skipped
    return samples, skipped


def load_model(model_path: str, dtype, device: str):
    import torch
    from transformers import AutoModelForImageTextToText

    model = AutoModelForImageTextToText.from_pretrained(
        model_path,
        dtype=dtype,
        device_map={"": device},
        attn_implementation="sdpa",
        local_files_only=True,
    )
    model.config.use_cache = False
    return model


def install_bidirectional_hooks(model):
    import torch
    from transformers.models.qwen3_5.modeling_qwen3_5 import Qwen3_5Attention

    decoder = model.model.language_model
    state = {"mask": None, "calls": 0}

    def full_attention_mask(module, args, kwargs):
        hidden = kwargs.get("hidden_states")
        if hidden is None:
            hidden = args[0]
        length = hidden.shape[1]
        mask = state["mask"]
        if mask is None or mask.shape[-1] != length or mask.device != hidden.device:
            mask = torch.zeros(
                (hidden.shape[0], 1, length, length), dtype=hidden.dtype, device=hidden.device
            )
            state["mask"] = mask
        kwargs["attention_mask"] = mask
        state["calls"] += 1
        return args, kwargs

    hooks = [
        module.register_forward_pre_hook(full_attention_mask, with_kwargs=True)
        for module in decoder.modules()
        if isinstance(module, Qwen3_5Attention)
    ]
    expected = decoder.config.layer_types.count("full_attention")
    if len(hooks) != expected:
        raise RuntimeError(f"full-attention layer count {len(hooks)} != {expected}")
    return decoder, hooks, state


def add_lora(model, args):
    from peft import LoraConfig, get_peft_model

    targets = [item.strip() for item in args.target_modules.split(",") if item.strip()]
    config = LoraConfig(
        r=args.lora_r,
        lora_alpha=args.lora_alpha,
        lora_dropout=args.lora_dropout,
        target_modules=targets,
        bias="none",
        task_type=None,
    )
    model.requires_grad_(False)
    model = get_peft_model(model, config)
    frozen = 0
    for name, parameter in model.named_parameters():
        if any(marker in name.lower() for marker in ("vision", "visual", "mtp")):
            parameter.requires_grad = False
            frozen += 1
    trainable = [parameter for parameter in model.parameters() if parameter.requires_grad]
    if not trainable:
        raise RuntimeError("LoRA injection produced no trainable parameters; check --target-modules")
    return model, trainable, len(trainable), frozen


def forward_logits(decoder, head, input_ids, candidate_ids, device="cuda"):
    import torch

    ids = torch.tensor([input_ids], dtype=torch.long, device=device)
    outputs = decoder(input_ids=ids, attention_mask=None, use_cache=False)
    hidden = outputs.last_hidden_state[0, -1].float()
    candidate = torch.tensor(candidate_ids, dtype=torch.long, device=hidden.device)
    logits = torch.mv(head.weight[candidate].float(), hidden)
    return logits


def evaluate(model, decoder, head, samples):
    import torch
    import torch.nn.functional as F

    model.eval()
    losses = []
    correct = 0
    with torch.inference_mode():
        for sample in samples:
            logits = forward_logits(decoder, head, sample["input_ids"], sample["candidate_ids"])
            target = torch.tensor([sample["target"]], dtype=torch.long, device=logits.device)
            losses.append(float(F.cross_entropy(logits.unsqueeze(0), target)))
            if int(logits.argmax().item()) == sample["target"]:
                correct += 1
    model.train()
    return {
        "loss": round(sum(losses) / len(losses), 6) if losses else None,
        "accuracy": round(correct / len(samples), 6) if samples else None,
        "n": len(samples),
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", required=True, help="local Piccolo-0.8B-VL directory")
    parser.add_argument("--train", type=Path, required=True)
    parser.add_argument("--dev", type=Path, help="optional separate dev file")
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--epochs", type=int, default=3)
    parser.add_argument("--lr", type=float, default=1e-4)
    parser.add_argument("--grad-accum", type=int, default=16)
    parser.add_argument("--max-seq-len", type=int, default=2048)
    parser.add_argument("--lora-r", type=int, default=32)
    parser.add_argument("--lora-alpha", type=int, default=64)
    parser.add_argument("--lora-dropout", type=float, default=0.05)
    parser.add_argument("--target-modules", default=DEFAULT_TARGETS)
    parser.add_argument("--max-steps", type=int, help="stop after N optimizer steps (smoke)")
    parser.add_argument("--eval-every", type=int, default=50, help="optimizer steps between dev checks")
    parser.add_argument("--no-grad-checkpoint", action="store_true", help="disable gradient checkpointing")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--limit", type=int, help="limit train samples for a smoke run")
    parser.add_argument("--dry-run", action="store_true", help="compile data only; no model load")
    parser.add_argument("--list-targets", action="store_true", help="print matching linear module names and exit")
    args = parser.parse_args(argv)

    import torch
    from transformers import AutoTokenizer

    if args.epochs < 1 or args.grad_accum < 1 or args.max_seq_len < 64:
        parser.error("epochs/grad-accum/max-seq-len are invalid")

    random.seed(args.seed)
    torch.manual_seed(args.seed)
    tokenizer = AutoTokenizer.from_pretrained(args.model, local_files_only=True)

    samples, skipped = build_samples(args.train, tokenizer, args.max_seq_len, "train", args.limit)
    if not samples:
        raise SystemExit("no training samples compiled; check --train and --max-seq-len")
    print(f"train samples: {len(samples)} | skipped: {len(skipped)}")
    if skipped[:10]:
        for item in skipped[:10]:
            print("  skip:", item)

    if args.dev:
        dev_samples, dev_skipped = build_samples(args.dev, tokenizer, args.max_seq_len, "dev")
    else:
        dev_samples, dev_skipped = build_samples(args.train, tokenizer, args.max_seq_len, "dev")
    print(f"dev samples: {len(dev_samples)} | skipped: {len(dev_skipped)}")

    if args.dry_run:
        lengths = sorted(len(sample["input_ids"]) for sample in samples)
        print(f"token p50={lengths[len(lengths)//2]} p95={lengths[int(len(lengths)*0.95)]} max={lengths[-1]}")
        print("dry run only; no model loaded")
        return 0

    if not torch.cuda.is_available():
        raise SystemExit("CUDA is not available")
    model = load_model(args.model, torch.bfloat16, "cuda")
    torch.cuda.reset_peak_memory_stats()
    if args.list_targets:
        targets = tuple(item.strip() for item in args.target_modules.split(",") if item.strip())
        names = [name for name, module in model.named_modules()
                 if isinstance(module, torch.nn.Linear) and name.endswith(targets)]
        print("\n".join(names))
        print(f"{len(names)} matching linear modules")
        return 0

    decoder, hooks, attention_state = install_bidirectional_hooks(model)
    head = model.get_output_embeddings()
    if head is None:
        raise SystemExit("model has no output embeddings")

    model, trainable, trainable_tensors, frozen = add_lora(model, args)
    print(f"trainable tensors: {trainable_tensors} | frozen vision/mtp tensors: {frozen}")
    try:
        model.enable_input_require_grads()
    except Exception:  # noqa: BLE001 - not all PEFT wrappers expose it
        pass
    if not args.no_grad_checkpoint:
        try:
            model.gradient_checkpointing_enable(gradient_checkpointing_kwargs={"use_reentrant": False})
            print("gradient checkpointing: on")
        except Exception as error:  # noqa: BLE001
            print(f"gradient checkpointing unavailable: {error}")

    optimizer = torch.optim.AdamW(trainable, lr=args.lr, weight_decay=0.0)
    steps_per_epoch = math.ceil(len(samples) / args.grad_accum)
    total_steps = steps_per_epoch * args.epochs
    if args.max_steps:
        total_steps = min(total_steps, args.max_steps)
    scheduler = torch.optim.lr_scheduler.LambdaLR(
        optimizer,
        lambda step: min(1.0, step / max(1, int(total_steps * 0.05)))
        * max(0.0, (total_steps - step) / max(1, total_steps - int(total_steps * 0.05))),
    )

    args.out.mkdir(parents=True, exist_ok=True)
    log_path = args.out / "train_log.jsonl"
    config = {
        "model": str(args.model),
        "train": str(args.train),
        "dev": str(args.dev) if args.dev else str(args.train),
        "epochs": args.epochs,
        "lr": args.lr,
        "grad_accum": args.grad_accum,
        "max_seq_len": args.max_seq_len,
        "lora_r": args.lora_r,
        "lora_alpha": args.lora_alpha,
        "lora_dropout": args.lora_dropout,
        "target_modules": args.target_modules,
        "seed": args.seed,
        "train_samples": len(samples),
        "dev_samples": len(dev_samples),
        "total_steps": total_steps,
        "skipped": skipped,
        "dev_skipped": dev_skipped,
    }
    (args.out / "training_config.json").write_text(json.dumps(config, ensure_ascii=False, indent=2) + "\n")

    model.train()
    optimizer.zero_grad(set_to_none=True)
    global_step = 0
    started = time.monotonic()
    best = None
    stop = False
    with log_path.open("w", encoding="utf-8") as log:
        for epoch in range(args.epochs):
            random.shuffle(samples)
            for index, sample in enumerate(samples):
                logits = forward_logits(decoder, head, sample["input_ids"], sample["candidate_ids"])
                target = torch.tensor([sample["target"]], dtype=torch.long, device=logits.device)
                loss = torch.nn.functional.cross_entropy(logits.unsqueeze(0), target) / args.grad_accum
                loss.backward()
                if (index + 1) % args.grad_accum == 0 or index + 1 == len(samples):
                    torch.nn.utils.clip_grad_norm_(trainable, 1.0)
                    optimizer.step()
                    scheduler.step()
                    optimizer.zero_grad(set_to_none=True)
                    global_step += 1
                    entry = {
                        "step": global_step,
                        "epoch": epoch + 1,
                        "loss": round(float(loss.item()) * args.grad_accum, 6),
                        "lr": scheduler.get_last_lr()[0],
                        "seconds": round(time.monotonic() - started, 2),
                        "max_memory_gib": round(torch.cuda.max_memory_allocated() / 2**30, 3),
                    }
                    log.write(json.dumps(entry) + "\n")
                    log.flush()
                    print(json.dumps(entry))
                    if global_step % args.eval_every == 0 and dev_samples:
                        metrics = evaluate(model, decoder, head, dev_samples)
                        print("dev:", metrics)
                        log.write(json.dumps({"step": global_step, "dev": metrics}) + "\n")
                        log.flush()
                        if best is None or (metrics["accuracy"] or 0) > best["accuracy"]:
                            best = {"accuracy": metrics["accuracy"] or 0, "step": global_step}
                            model.save_pretrained(args.out / "best_adapter")
                    if args.max_steps and global_step >= args.max_steps:
                        stop = True
                        break
            if stop:
                break

        model.save_pretrained(args.out / "adapter")
        if dev_samples:
            final = evaluate(model, decoder, head, dev_samples)
        else:
            final = None
        config["final_dev"] = final
        config["best_dev"] = best
        config["seconds"] = round(time.monotonic() - started, 2)
        (args.out / "training_config.json").write_text(
            json.dumps(config, ensure_ascii=False, indent=2) + "\n"
        )
        print("final dev:", final)
        print(f"adapter: {args.out / 'adapter'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
