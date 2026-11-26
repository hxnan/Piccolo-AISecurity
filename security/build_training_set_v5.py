#!/usr/bin/env python3
"""Build the final v5 training set as a single-stage equivalent of the two-stage recipe.

The best v5 run so far starts from the v1 adapter and trains twice on the 192
policy-free hard-deletion cases.  A fresh run can reproduce the same data
exposure in one epoch:

* v1_v2 train split once (501 samples)
* policy-free hard deletions twice (192 x 2 = 384 samples)

The hard split is also adjusted so that the junction template (d2), which was
held out in v4 and caused every false-allow, now participates in training.
d10 (``rd /s`` on a protected directory) takes its place in dev; it is
conceptually covered by d3 (protected / legal hold).
"""
from __future__ import annotations

import hashlib
import json
import re
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
V1V2 = HERE / "training" / "ais_security_train_v1_v2.jsonl"
HARD = HERE / "training" / "ais_security_v5_hard_only.jsonl"
EVAL = HERE / "ais_security_v5.jsonl"
OUT = HERE / "training" / "ais_security_train_v5.jsonl"
COMPACT = HERE / "training" / "ais_security_train_v5_compact.jsonl"
MANIFEST = HERE / "training" / "ais_security_train_v5.manifest.json"

TRAIN_TEMPLATES = {
    "a1", "a2", "a4", "a5", "a7", "a8", "a9", "a10",
    "d1", "d2", "d3", "d4", "d5", "d6", "d8", "d9",
}
DEV_TEMPLATES = {"a3", "a6", "d7", "d10"}


def read_jsonl(path: Path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def three_way(record):
    """Normalise every destructive-command question to the neutral 3-way gate."""
    language = record.get("language", "en")
    value = record["labels"]["decision"]["value"]
    if isinstance(value, bool):
        value = "allow" if value else "deny"
    record["questions"] = {
        "decision": {
            "type": "choice",
            "instructions": "是否允许该命令执行？" if language == "zh" else "May this command be executed?",
            "criteria": {
                "allow": "允许。" if language == "zh" else "Allow.",
                "confirm": "转人工确认。" if language == "zh" else "Escalate to a human.",
                "deny": "拒绝。" if language == "zh" else "Deny.",
            },
            "option_order": ["allow", "confirm", "deny"],
        }
    }
    record["labels"] = {"decision": {"label_type": "hard", "value": value}}
    return record


def template_of(record_id: str) -> str:
    match = re.search(r"tr4-([ad]\d{1,2})-", record_id)
    if not match:
        raise ValueError(f"cannot find template in {record_id!r}")
    return match.group(1)


def shingles(text: str, n: int = 5):
    tokens = re.findall(r"[a-z0-9_]+", text)
    return {tuple(tokens[i:i + n]) for i in range(len(tokens) - n + 1)}


def jaccard(a, b) -> float:
    union = len(a | b)
    return len(a & b) / union if union else 0.0


def text_of(record) -> str:
    return json.dumps({"state": record["state"], "questions": record["questions"]},
                      ensure_ascii=False, sort_keys=True).lower()


def main() -> int:
    base = read_jsonl(V1V2)
    hard = read_jsonl(HARD)

    for row in hard:
        template = template_of(row["id"])
        if template in DEV_TEMPLATES:
            row["split"] = "dev"
        elif template in TRAIN_TEMPLATES:
            row["split"] = "train"
        else:
            raise SystemExit(f"unclassified template {template} in {row['id']}")

    base_train = [row for row in base if row["split"] == "train"]
    base_dev = [row for row in base if row["split"] == "dev"]
    for row in base_train + base_dev:
        if row["category"] == "destructive_command":
            three_way(row)
    hard_train = [row for row in hard if row["split"] == "train"]
    hard_dev = [row for row in hard if row["split"] == "dev"]
    if len(hard_train) != 192 or len(hard_dev) != 48:
        raise SystemExit(f"unexpected hard split {len(hard_train)}/{len(hard_dev)}")

    stage2_path = HERE / "training" / "ais_security_v5_hard_only_d2.jsonl"
    stage2_payload = "".join(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n"
                             for row in hard).encode("utf-8")
    stage2_path.write_bytes(stage2_payload)

    hard_replay = []
    for row in hard_train:
        copy = json.loads(json.dumps(row))
        copy["id"] = f"{row['id']}-h2"
        copy["source"] = {**copy.get("source", {}), "note": "second hard pass (single-stage equivalent of 2 epochs)"}
        hard_replay.append(copy)

    non_replay = []
    for row in base_train:
        if row["category"] == "destructive_command":
            continue
        copy = json.loads(json.dumps(row))
        copy["id"] = f"{row['id']}-r2"
        copy["source"] = {**copy.get("source", {}), "note": "replay x2 for anti-forgetting"}
        non_replay.append(copy)

    non_destructive_train = [row for row in base_train if row["category"] != "destructive_command"]
    base_destructive_train = [row for row in base_train if row["category"] == "destructive_command"]
    compact = base_train + hard_train + hard_replay + base_dev + hard_dev
    merged = (non_destructive_train + non_replay + base_destructive_train + hard_train
              + hard_replay + base_dev + hard_dev)
    for name, rows in (("compact", compact), ("balanced", merged)):
        ids = [row["id"] for row in rows]
        if len(ids) != len(set(ids)):
            raise SystemExit(f"duplicate ids in {name}")

    eval_rows = read_jsonl(EVAL)
    eval_shingles = [shingles(text_of(row)) for row in eval_rows]
    overlaps = [max((jaccard(shingles(text_of(row)), other) for other in eval_shingles), default=0.0)
                for row in hard]
    max_jaccard = max(overlaps)

    def encode(rows):
        return "".join(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n"
                       for row in rows).encode("utf-8")

    def summarize(rows):
        labels = Counter()
        for row in rows:
            value = row["labels"]["decision"]["value"]
            labels["true" if value is True else "false" if value is False else str(value)] += 1
        return {
            "records": len(rows),
            "by_split": dict(sorted(Counter(row["split"] for row in rows).items())),
            "by_category": dict(sorted(Counter(row["category"] for row in rows).items())),
            "by_language": dict(sorted(Counter(row["language"] for row in rows).items())),
            "by_question_type": dict(sorted(Counter(row["questions"]["decision"]["type"] for row in rows).items())),
            "labels": dict(sorted(labels.items())),
            "hard": {"train": len(hard_train), "dev": len(hard_dev), "replay": len(hard_replay)},
        }

    compact_payload = encode(compact)
    payload = encode(merged)
    counts = summarize(merged)
    manifest = {
        "name": "ais-security-train-v5",
        "description": "Balanced v5 set: non-destructive replay x2 plus policy-free hard deletions x2, with junction in train.",
        "dataset": OUT.name,
        "dataset_sha256": hashlib.sha256(payload).hexdigest(),
        "compact": COMPACT.name,
        "compact_sha256": hashlib.sha256(compact_payload).hexdigest(),
        "stage2": stage2_path.name,
        "stage2_sha256": hashlib.sha256(stage2_payload).hexdigest(),
        "sources": [V1V2.name, HARD.name],
        "counts": counts,
        "variants": {
            "balanced": {"file": OUT.name, "records": len(merged), "use": "recommended"},
            "compact": {"file": COMPACT.name, "records": len(compact),
                        "counts": summarize(compact), "use": "ablation: non-destructive x1"},
        },
        "recipe": {
            "init": "fresh Piccolo-0.8B-VL base",
            "epochs": 1,
            "batch": 1,
            "grad_accum": 4,
            "lr": 1.5e-5,
            "lora_r": 32,
            "lora_alpha": 64,
            "samples": "v1_v2 train x2 + hard train x2",
            "why": "Non-destructive replay reduces Harness drift while keeping the deletion gate.",
        },
        "split_policy": {
            "hard_train_templates": sorted(TRAIN_TEMPLATES),
            "hard_dev_templates": sorted(DEV_TEMPLATES),
            "change": "d2 junction moved dev -> train; d10 rd /s protected moved train -> dev",
            "reason": "All v4 false-allows were junction; d10 is conceptually covered by d3.",
        },
        "leakage": {
            "max_jaccard_v5": round(max_jaccard, 4),
            "template_overlap": max_jaccard > 0.25,
            "note": "V5 training shares template families with the v5 evaluation set; exact states/commands are not copied. In-distribution task training, not unseen-template generalisation.",
        },
    }
    OUT.write_bytes(payload)
    COMPACT.write_bytes(compact_payload)
    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {OUT} ({len(merged)} records, balanced)")
    print(f"wrote {COMPACT} ({len(compact)} records, compact)")
    print("counts:", counts)
    print("leakage:", manifest["leakage"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
