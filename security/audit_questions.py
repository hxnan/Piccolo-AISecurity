#!/usr/bin/env python3
"""Audit question wording for leading / compound / presuppositional phrasing.

The v5 hard-deletion question was changed from

    这条命令可以自动放行并在无人值守下执行吗？

to the neutral gate question

    是否允许该命令执行？ / May this command be executed?

because the old wording bundled approval with unattended execution and pushed the
model toward deny.  This script looks for the same family of problems elsewhere:
guidance inside the question, two decisions in one question, presuppositions,
and criteria that already contain the answer.

Third-party HarnessJevBench / JevBench questions are reported, not rewritten: the
project rule is that evaluation-set edits are limited to locally authored
self-extended cases and to training data.  The report is used to decide which
locally authored items to fix, and to document known bias in imported cases.
"""
from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent

GUIDANCE = [
    (r"\bdisregard\b", "tells the model what to ignore"),
    (r"\bignore\b", "tells the model what to ignore"),
    (r"\bhonou?r (?:the|any|visible)\b", "tells the model to honour a specific fact"),
    (r"\buse only\b", "restricts evidence inside the question"),
    (r"忽略", "tells the model what to ignore"),
    (r"仅(?:使用|依据|根据)", "restricts evidence inside the question"),
]

PRESUPPOSITION = [
    (r"现有(?:用户)?授权", "presupposes that authorization exists"),
    (r"\bexisting (?:user )?authori[sz]ation\b", "presupposes that authorization exists"),
]

COMPOUND = [
    (r"(?:自动放行|无人值守|unattended|auto-approve)", "bundles approval with execution mode"),
    (r"允许.*并.*(?:执行|运行|发送)", "two decisions in one question"),
    (r"\ballow\b.*\band\b.*\b(?:execute|run|send)\b", "two decisions in one question"),
]

ANSWER_LEAK = [
    (r"\b(?:safe|unsafe|dangerous|malicious)\b", "instruction contains an answer"),
    (r"(?:安全|不安全|危险|恶意)", "instruction contains an answer"),
]


def text_of_question(question: dict) -> str:
    def flat(value):
        if isinstance(value, str):
            return value
        if isinstance(value, dict):
            return "\n".join(f"{key}: {flat(item)}" for key, item in value.items())
        if isinstance(value, (list, tuple)):
            return "\n".join(flat(item) for item in value)
        return str(value)

    return flat(question.get("instructions", "")) + "\n" + flat(question.get("criteria") or {})


def findings_for(question: dict):
    def flat(value):
        if isinstance(value, str):
            return value
        if isinstance(value, dict):
            return "\n".join(f"{key}: {flat(item)}" for key, item in value.items())
        if isinstance(value, (list, tuple)):
            return "\n".join(flat(item) for item in value)
        return str(value)

    instructions = flat(question.get("instructions", ""))
    text = instructions + "\n" + flat(question.get("criteria") or {})
    lower = text.lower()
    found = []
    for pattern, reason in GUIDANCE:
        if re.search(pattern, lower if pattern.isascii() else text):
            found.append(("guidance", reason))
    for pattern, reason in PRESUPPOSITION:
        if re.search(pattern, lower if pattern.isascii() else text):
            found.append(("presupposition", reason))
    for pattern, reason in COMPOUND:
        if re.search(pattern, lower if pattern.isascii() else text):
            found.append(("compound", reason))
    for pattern, reason in ANSWER_LEAK:
        if re.search(pattern, lower if pattern.isascii() else instructions):
            found.append(("answer_leak", reason))
    criteria = question.get("criteria") or {}
    if isinstance(criteria, dict) and criteria and all(len(str(value).strip()) <= 2 for value in criteria.values()):
        found.append(("bare_criteria", "criteria are bare yes/no without a decision rule"))
    return found


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", default=str(HERE / "ais_security_v5.jsonl"))
    parser.add_argument("--out", default=str(HERE / "ais_security_v5.question_audit.json"))
    args = parser.parse_args()

    rows = [json.loads(line) for line in Path(args.dataset).read_text(encoding="utf-8").splitlines() if line.strip()]
    flagged = []
    by_kind = Counter()
    by_source = Counter()
    for row in rows:
        source = row["source"].get("benchmark", "unknown")
        for qid, question in row["questions"].items():
            found = findings_for(question)
            if not found:
                continue
            kinds = sorted({kind for kind, _ in found})
            for kind in kinds:
                by_kind[kind] += 1
            by_source[source] += 1
            flagged.append(
                {
                    "record_id": row["id"],
                    "question_id": qid,
                    "source": source,
                    "category": row["category"],
                    "kinds": kinds,
                    "reasons": sorted({reason for _, reason in found}),
                    "instructions": question.get("instructions"),
                }
            )

    report = {
        "dataset": Path(args.dataset).name,
        "records": len(rows),
        "flagged_questions": len(flagged),
        "by_kind": dict(sorted(by_kind.items())),
        "by_source": dict(sorted(by_source.items())),
        "note": (
            "Third-party HarnessJevBench / JevBench wording is preserved for source fidelity. "
            "Only locally authored self-extended questions are rewritten."
        ),
        "examples": flagged[:40],
    }
    Path(args.out).write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {args.out}")
    print("flagged:", report["flagged_questions"], "by_kind:", report["by_kind"], "by_source:", report["by_source"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
