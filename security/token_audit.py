#!/usr/bin/env python3
"""Count prompt tokens for the AISecurity set before starting a GPU server.

Uses the checkpoint tokenizer and the reference FlexDM compiler, so the counts
match what ``/v1/systemone`` will build. Run this on the GPU host after the
model is downloaded and before launching SGLang; it needs no GPU.

    python security/token_audit.py \
        --model /models/Piccolo-0.8B-VL \
        --max-context 65535 \
        --output var/eval/token_audit.json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from types import SimpleNamespace

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT / "inference" / "reference"))

from piccolo_inference import FlexCompiler  # noqa: E402
from piccolo_layout import Layout, render_question  # noqa: E402


def read_jsonl(path: Path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def percentile(values, q):
    values = sorted(values)
    if not values:
        return None
    index = min(len(values) - 1, max(0, int(round((len(values) - 1) * q))))
    return values[index]


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, default=HERE / "ais_security_v5.jsonl")
    parser.add_argument("--model", required=True, help="local checkpoint directory with the tokenizer")
    parser.add_argument("--max-context", type=int, default=65535, help="server row limit (SGLang plugin default)")
    parser.add_argument("--tokens-per-second", type=float, default=8000.0, help="prefill estimate for planning")
    parser.add_argument("--overhead", type=float, default=0.25, help="seconds per request for planning")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)

    from transformers import AutoTokenizer

    tokenizer = AutoTokenizer.from_pretrained(args.model, local_files_only=True)
    compiler = FlexCompiler(
        tokenizer,
        SimpleNamespace(Layout=Layout, render_question=render_question),
        max_context=262144,
        twice_max_tokens=3000,
    )

    records = read_jsonl(args.dataset)
    rows = []
    for record in records:
        for qid, question in record["questions"].items():
            try:
                compiled, _ = compiler.compile({"state": record["state"], "questions": {qid: question}})
                tokens = len(compiled[0].input_ids)
                repeated = compiled[0].repeated
                error = None
            except Exception as exc:  # noqa: BLE001 - report and continue
                tokens, repeated, error = None, None, f"{type(exc).__name__}: {exc}"
            rows.append(
                {
                    "record_id": record["id"],
                    "question_id": qid,
                    "source": record["source"]["benchmark"],
                    "category": record["category"],
                    "tokens": tokens,
                    "repeated": repeated,
                    "over_limit": tokens is not None and tokens > args.max_context,
                    "error": error,
                }
            )

    known = [row["tokens"] for row in rows if row["tokens"] is not None]
    total = sum(known)
    over = [row for row in rows if row["over_limit"]]
    estimate = total / args.tokens_per_second + len(rows) * args.overhead
    result = {
        "dataset": str(args.dataset),
        "model": str(args.model),
        "max_context": args.max_context,
        "questions": len(rows),
        "questions_measured": len(known),
        "failed_to_compile": sum(1 for row in rows if row["tokens"] is None),
        "total_tokens": total,
        "p50_tokens": percentile(known, 0.5),
        "p95_tokens": percentile(known, 0.95),
        "max_tokens": max(known) if known else None,
        "over_limit": over,
        "estimated_seconds": round(estimate, 1),
        "assumptions": {
            "prefill_tokens_per_second": args.tokens_per_second,
            "per_request_overhead_seconds": args.overhead,
        },
        "rows": rows,
    }

    print(f"questions: {len(rows)} | measured: {len(known)} | failed: {result['failed_to_compile']}")
    print(f"tokens total {total} | p50 {result['p50_tokens']} | p95 {result['p95_tokens']} | max {result['max_tokens']}")
    print(f"over {args.max_context}: {len(over)}")
    for row in over[:20]:
        print(f"  {row['record_id']}/{row['question_id']} = {row['tokens']} tokens")
    print(f"rough prefill+overhead estimate: {result['estimated_seconds']} s")
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
