#!/usr/bin/env python3
"""Build failure-driven training set v2 and merge it with v1 (plan B).

Reads a baseline ``scores.jsonl``, finds categories below the accuracy
threshold, regenerates extra samples for those categories from the template
families (new seed, new entities), and writes a merged v1+v2 training file.

This is template-level oversampling, not evaluation-item copying. The generated
states still pass the same leakage checks against the evaluation set.

Usage:
    python security/build_v2_from_failures.py \
        --scores var/eval/0.8b-baseline/scores.jsonl \
        --v1 security/training/ais_security_train_v1.jsonl \
        --out-dir security/training \
        --threshold 0.80 --scale 0.5
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))

import build_training_set as builder  # noqa: E402


def read_jsonl(path: Path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def category_profile(scores):
    stats = defaultdict(lambda: [0, 0])
    for row in scores:
        category = row.get("category") or "unknown"
        stats[category][1] += 1
        if row.get("correct"):
            stats[category][0] += 1
    return {
        category: {
            "n": total,
            "correct": correct,
            "accuracy": round(correct / total, 6) if total else None,
        }
        for category, (correct, total) in sorted(stats.items())
    }


def counts(rows):
    labels = Counter(
        "true" if row["labels"]["decision"]["value"] is True else
        "false" if row["labels"]["decision"]["value"] is False else
        str(row["labels"]["decision"]["value"])
        for row in rows
    )
    return {
        "records": len(rows),
        "by_split": dict(sorted(Counter(row["split"] for row in rows).items())),
        "by_category": dict(sorted(Counter(row["category"] for row in rows).items())),
        "by_language": dict(sorted(Counter(row["language"] for row in rows).items())),
        "by_question_type": dict(sorted(Counter(row["questions"]["decision"]["type"] for row in rows).items())),
        "labels": dict(sorted(labels.items())),
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scores", type=Path, required=True)
    parser.add_argument("--v1", type=Path, default=HERE / "training" / "ais_security_train_v1.jsonl")
    parser.add_argument("--out-dir", type=Path, default=HERE / "training")
    parser.add_argument("--threshold", type=float, default=0.80,
                        help="categories below this accuracy get extra samples")
    parser.add_argument("--scale", type=float, default=0.5,
                        help="fraction of the generated v2 samples to keep")
    args = parser.parse_args(argv)

    scores = read_jsonl(args.scores)
    profile = category_profile(scores)
    failed = {
        category: value for category, value in profile.items()
        if value["accuracy"] is not None and value["accuracy"] < args.threshold
    }
    if not failed:
        print("no category below threshold; v2 is empty")

    # New seed and record prefix so v2 ids never collide with v1.
    seed = builder.SEED + int(hashlib.sha256(args.scores.read_bytes()).hexdigest()[:8], 16)
    builder.RNG.seed(seed)
    builder.COUNTER.clear()
    builder.RECORD_PREFIX = "tr2"

    generated = []
    for generator in (
        builder.gen_destructive, builder.gen_authorization, builder.gen_injection,
        builder.gen_data, builder.gen_access, builder.gen_state, builder.gen_context,
        builder.gen_validation, builder.gen_scoring,
    ):
        generated.extend(generator())

    v2 = [row for row in generated if row["category"] in failed]
    for row in v2:
        row["split"] = "train"
    if args.scale < 1.0 and v2:
        v2 = v2[: max(1, int(len(v2) * args.scale))]

    v1 = read_jsonl(args.v1)
    merged = v1 + v2
    merged.sort(key=lambda row: row["id"])

    eval_rows = read_jsonl(HERE / "ais_security_v1.jsonl")
    report = builder.leakage_report(merged, eval_rows)
    if report["rejected"]:
        for item in report["rejected"][:20]:
            print("leakage reject:", item[0], item[1])
        raise SystemExit(f"{report['rejected_count']} records rejected for leakage")

    payload = "".join(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n" for row in merged).encode("utf-8")
    manifest = {
        "name": "ais-security-train-v1-v2",
        "description": "Failure-driven v2 merged with the v1 generalisation set.",
        "dataset": "ais_security_train_v1_v2.jsonl",
        "dataset_sha256": hashlib.sha256(payload).hexdigest(),
        "v1": str(args.v1),
        "v1_sha256": hashlib.sha256(args.v1.read_bytes()).hexdigest(),
        "scores": str(args.scores),
        "scores_sha256": hashlib.sha256(args.scores.read_bytes()).hexdigest(),
        "threshold": args.threshold,
        "scale": args.scale,
        "seed": seed,
        "failure_profile": profile,
        "failed_categories": {key: value for key, value in failed.items()},
        "v2_counts": counts(v2),
        "merged_counts": counts(merged),
        "leakage": report,
        "method": {
            "v2": "Regenerate template-family samples for categories below threshold with a new seed; no evaluation item is copied.",
            "dev": "v1 dev is unchanged; v2 is train-only.",
        },
    }
    manifest_bytes = (json.dumps(manifest, ensure_ascii=False, indent=2) + "\n").encode("utf-8")

    args.out_dir.mkdir(parents=True, exist_ok=True)
    dataset_path = args.out_dir / "ais_security_train_v1_v2.jsonl"
    manifest_path = args.out_dir / "ais_security_train_v1_v2.manifest.json"
    dataset_path.write_bytes(payload)
    manifest_path.write_bytes(manifest_bytes)
    print(f"wrote {dataset_path} ({len(merged)} records; v2 {len(v2)})")
    print(f"wrote {manifest_path}")
    print("failed categories:", {k: v["accuracy"] for k, v in failed.items()})
    print("leakage:", report["max_jaccard"], report["max_command_lcs"], report["rejected_count"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
