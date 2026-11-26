#!/usr/bin/env python3
"""Build the v2 AISecurity set: v1 non-destructive cases + 60 hard deletion cases.

v1 is preserved unchanged for the published baseline/LoRA report. v2 replaces
the 30 easy deletion cases with 60 hard cases (30 allow / 30 deny) that include
scary-but-safe commands and harmless-looking escapes.

Run:
    python security/build_hard_deletion_set.py
    python security/build_dataset_v2.py
"""
from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
V1 = HERE / "ais_security_v1.jsonl"
HARD = HERE / "extended" / "deletion_guard_v2.jsonl"
TRAIN = HERE / "training" / "ais_security_train_v1.jsonl"
OUT = HERE / "ais_security_v2.jsonl"
MANIFEST = HERE / "ais_security_v2.manifest.json"


def read_jsonl(path: Path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def text_of(record):
    return json.dumps({"state": record["state"], "questions": record["questions"]},
                      ensure_ascii=False, sort_keys=True).lower()


def shingles(text, n=5):
    import re
    tokens = re.findall(r"[a-z0-9_]+", text)
    return {tuple(tokens[i:i + n]) for i in range(len(tokens) - n + 1)}


def jaccard(a, b):
    union = len(a | b)
    return len(a & b) / union if union else 0.0


def longest_common_substring(a: str, b: str) -> int:
    best = 0
    prev = [0] * (len(b) + 1)
    for ch in a:
        cur = [0] * (len(b) + 1)
        for j, other in enumerate(b, 1):
            if ch == other:
                cur[j] = prev[j - 1] + 1
                if cur[j] > best:
                    best = cur[j]
        prev = cur
    return best


def validate_record(record):
    q = record["questions"]["decision"]
    label = record["labels"]["decision"]
    if label.get("label_type") != "hard":
        raise SystemExit(f"{record['id']}: not a hard label")
    if q["type"] == "noul":
        if not isinstance(label["value"], bool):
            raise SystemExit(f"{record['id']}: noul label is not bool")
    elif q["type"] == "choice":
        keys = [str(k) for k in (q.get("option_order") or q["criteria"])]
        if str(label["value"]) not in keys:
            raise SystemExit(f"{record['id']}: label not in criteria")
    elif q["type"] == "score":
        if not str(label["value"]).isdigit() or int(label["value"]) >= len(q["criteria"]):
            raise SystemExit(f"{record['id']}: invalid score label")
    else:
        raise SystemExit(f"{record['id']}: unknown question type")


def main() -> int:
    v1 = read_jsonl(V1)
    hard = read_jsonl(HARD)
    train = read_jsonl(TRAIN) if TRAIN.is_file() else []
    non_destructive = [row for row in v1 if row["category"] != "destructive_command"]
    if len(non_destructive) != 195:
        raise SystemExit(f"expected 195 non-destructive v1 records, got {len(non_destructive)}")
    if len(hard) != 60:
        raise SystemExit(f"expected 60 hard records, got {len(hard)}")

    digest = hashlib.sha256(HARD.read_bytes()).hexdigest()
    hard_records = []
    for row in hard:
        validate_record(row)
        hard_records.append(
            {
                "id": "ais-x-" + row["id"],
                "category": "destructive_command",
                "source": {
                    "benchmark": "self-extended",
                    "source_id": row["id"],
                    "revision": digest,
                    "split": "self_extended",
                    "language": row["language"],
                    "difficulty": row["difficulty"],
                    "license": "Apache-2.0",
                },
                "state": row["state"],
                "questions": row["questions"],
                "labels": row["labels"],
            }
        )

    merged = non_destructive + hard_records
    merged.sort(key=lambda row: row["id"])

    # Leakage against v1 and the training set; the hard cases are new, but keep
    # the same thresholds used for the training-set builder.
    v1_shingles = [shingles(text_of(row)) for row in v1]
    train_shingles = [shingles(text_of(row)) for row in train]
    v1_commands = []
    for row in v1:
        state = row.get("state")
        if isinstance(state, dict):
            for key in ("command", "proposed_command"):
                if isinstance(state.get(key), str):
                    v1_commands.append((row["id"], state[key].lower()))
    max_v1 = max_train = max_lcs = 0.0
    rejects = []
    for row in hard_records:
        grams = shingles(text_of(row))
        score_v1 = max((jaccard(grams, other) for other in v1_shingles), default=0.0)
        score_train = max((jaccard(grams, other) for other in train_shingles), default=0.0)
        max_v1 = max(max_v1, score_v1)
        max_train = max(max_train, score_train)
        command = row["state"]["command"].lower()
        for key, other in v1_commands:
            lcs = longest_common_substring(command, other)
            max_lcs = max(max_lcs, lcs)
            if lcs > 60:
                rejects.append((row["id"], "command_lcs", lcs, key))
                break
        if score_v1 > 0.25:
            rejects.append((row["id"], "jaccard_v1", score_v1))
        if score_train > 0.25:
            rejects.append((row["id"], "jaccard_train", score_train))

    if rejects:
        for item in rejects[:20]:
            print("leakage reject:", item)
        raise SystemExit(f"{len(rejects)} hard records rejected for leakage")

    payload = "".join(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n"
                      for row in merged).encode("utf-8")
    labels = Counter()
    for row in merged:
        for label in row["labels"].values():
            value = label["value"]
            labels["true" if value is True else "false" if value is False else str(value)] += 1
    manifest = {
        "name": "ais-security-v2",
        "description": "v1 non-destructive cases plus 60 hard destructive-command cases.",
        "dataset": OUT.name,
        "dataset_sha256": hashlib.sha256(payload).hexdigest(),
        "v1": V1.name,
        "v1_sha256": hashlib.sha256(V1.read_bytes()).hexdigest(),
        "hard_set": str(HARD.relative_to(HERE)).replace("\\", "/"),
        "hard_set_sha256": digest,
        "counts": {
            "records": len(merged),
            "questions": sum(len(row["questions"]) for row in merged),
            "by_source": dict(sorted(Counter(row["source"]["benchmark"] for row in merged).items())),
            "by_category": dict(sorted(Counter(row["category"] for row in merged).items())),
            "by_language": dict(sorted(Counter(row["source"].get("language") or "unknown" for row in merged).items())),
            "by_question_type": dict(sorted(Counter(
                question["type"] for row in merged for question in row["questions"].values()).items())),
            "hard_labels": dict(sorted(Counter(
                "true" if row["labels"]["decision"]["value"] is True else "false"
                for row in hard_records).items())),
        },
        "selection": {
            "rule": "v1 non-destructive records unchanged; 30 easy deletion cases replaced by 60 hard cases",
            "hard_templates": [
                "empty disposable directory with rm -rf (allow)",
                "dry-run-proven single match with find (allow)",
                "empty disposable directory with Remove-Item -Recurse (allow)",
                "verified disposable mirror with rsync --delete (allow)",
                "cd .. still inside scope (allow)",
                "dry-run-proven wildcard single match (allow)",
                "exact file via .. outside scope (deny)",
                "innocuous junction to production (deny)",
                "exact file inside scope under legal hold (deny)",
                "hardlink to production (deny)",
                "variable resolves outside scope (deny)",
                "protected only-copy mirror (deny)",
            ],
            "hard_labels": "30 allow / 30 deny; 36 zh / 24 en; difficulty 4-5",
        },
        "leakage": {
            "thresholds": {"jaccard_5gram": 0.25, "command_lcs_chars": 60},
            "max_jaccard_v1": round(max_v1, 4),
            "max_jaccard_train": round(max_train, 4),
            "max_command_lcs": max_lcs,
            "rejected": rejects,
        },
    }
    OUT.write_bytes(payload)
    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {OUT} ({len(merged)} records, {manifest['counts']['questions']} questions)")
    print(f"wrote {MANIFEST}")
    print("hard labels:", manifest["counts"]["hard_labels"])
    print("leakage:", manifest["leakage"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
