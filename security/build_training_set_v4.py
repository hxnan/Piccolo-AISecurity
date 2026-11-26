#!/usr/bin/env python3
"""Build the v4 training set: v1 non-destructive cases + policy-free hard deletions."""
from __future__ import annotations

import hashlib
import json
import re
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
V1 = HERE / "training" / "ais_security_train_v1.jsonl"
V4 = HERE / "training" / "policy_free_deletion_v4.jsonl"
V3_EVAL = HERE / "ais_security_v3.jsonl"
OUT = HERE / "training" / "ais_security_train_v4.jsonl"
MANIFEST = HERE / "training" / "ais_security_train_v4.manifest.json"


def read_jsonl(path: Path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def text_of(record):
    return json.dumps({"state": record["state"], "questions": record["questions"]},
                      ensure_ascii=False, sort_keys=True).lower()


def shingles(text, n=5):
    tokens = re.findall(r"[a-z0-9_]+", text)
    return {tuple(tokens[i:i + n]) for i in range(len(tokens) - n + 1)}


def jaccard(a, b):
    union = len(a | b)
    return len(a & b) / union if union else 0.0


def main() -> int:
    v1 = read_jsonl(V1)
    v1 = [row for row in v1 if row["category"] != "destructive_command"]
    hard = read_jsonl(V4)
    digest = hashlib.sha256(V4.read_bytes()).hexdigest()
    for row in hard:
        row["category"] = "destructive_command"
        row["source"] = {
            "benchmark": "self-generated",
            "revision": digest,
            "license": "Apache-2.0",
            "note": "policy-free hard deletion training",
        }
    rows = v1 + hard
    ids = [row["id"] for row in rows]
    if len(ids) != len(set(ids)):
        raise SystemExit("duplicate ids")

    eval_rows = read_jsonl(V3_EVAL)
    eval_shingles = [shingles(text_of(row)) for row in eval_rows]
    eval_commands = []
    for row in eval_rows:
        state = row.get("state")
        if isinstance(state, dict) and isinstance(state.get("command"), str):
            eval_commands.append((row["id"], state["command"].lower()))
    max_jaccard = 0.0
    max_lcs = 0
    rejects = []
    for row in hard:
        grams = shingles(text_of(row))
        score = max((jaccard(grams, other) for other in eval_shingles), default=0.0)
        max_jaccard = max(max_jaccard, score)
        command = row["state"]["command"].lower()
        for key, other in eval_commands:
            # simple longest common substring, commands are short
            best = 0
            prev = [0] * (len(other) + 1)
            for ch in command:
                cur = [0] * (len(other) + 1)
                for j, value in enumerate(other, 1):
                    if ch == value:
                        cur[j] = prev[j - 1] + 1
                        best = max(best, cur[j])
                prev = cur
            max_lcs = max(max_lcs, best)
            if best > 60:
                rejects.append((row["id"], "command_lcs", best, key))
                break
        # Jaccard >0.25 is reported as template overlap, not rejected: V4 is
        # in-distribution task training, not an unseen-template test.
        if score > 0.25:
            pass
    if rejects:
        for item in rejects[:10]:
            print("reject:", item)
        raise SystemExit(f"{len(rejects)} records rejected")

    payload = "".join(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n"
                      for row in rows).encode("utf-8")
    counts = {
        "records": len(rows),
        "by_split": dict(sorted(Counter(row["split"] for row in rows).items())),
        "by_category": dict(sorted(Counter(row["category"] for row in rows).items())),
        "by_language": dict(sorted(Counter(row["language"] for row in rows).items())),
        "by_question_type": dict(sorted(Counter(row["questions"]["decision"]["type"] for row in rows).items())),
        "labels": dict(sorted(Counter(
            "true" if row["labels"]["decision"]["value"] is True else "false"
            for row in rows).items())),
    }
    manifest = {
        "name": "ais-security-train-v4",
        "description": "v1 non-destructive training cases plus 240 policy-free hard deletion cases.",
        "dataset": OUT.name,
        "dataset_sha256": hashlib.sha256(payload).hexdigest(),
        "v1_source": V1.name,
        "hard_source": V4.name,
        "hard_sha256": digest,
        "counts": counts,
        "method": {
            "v1": "non-destructive cases from ais_security_train_v1 unchanged",
            "v4": "policy-free deletion cases; state has task/shell/cwd/command/environment only",
            "targets": "hard labels; derive one-hot or smoothed candidate targets at training time",
        },
        "leakage": {
            "thresholds": {"jaccard_5gram": 0.25, "command_lcs_chars": 60},
            "max_jaccard_v3": round(max_jaccard, 4),
            "max_command_lcs": max_lcs,
            "rejected": rejects,
            "template_overlap": max_jaccard > 0.25,
            "note": "V4 shares template families with V3; exact states and commands are not copied. Use the v3 result as in-distribution task learning, not unseen-template generalisation.",
        },
    }
    OUT.write_bytes(payload)
    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {OUT} ({len(rows)} records)")
    print(f"wrote {MANIFEST}")
    print("counts:", counts)
    print("leakage:", manifest["leakage"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
