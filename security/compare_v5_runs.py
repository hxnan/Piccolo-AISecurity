#!/usr/bin/env python3
"""Render the v5 comparison tables used by results/0.8b-v5/REPORT.md."""
from __future__ import annotations

import argparse
import collections
import json
from pathlib import Path

TEMPLATES = ["A1", "A2", "A3", "A4", "A5", "A6", "D1", "D2", "D3", "D4", "D5", "D6"]
TEMPLATE_MEANING = {
    "A1": "rm -rf 空目录（allow）",
    "A2": "find 唯一匹配（allow）",
    "A3": "Remove-Item 空目录（allow，dev）",
    "A4": "rsync --delete 镜像（allow）",
    "A5": "cd .. 仍在 scope（allow）",
    "A6": "通配符唯一匹配（allow，dev）",
    "D1": ".. 精确越界（deny）",
    "D2": "junction（deny）",
    "D3": "protected / legal hold（deny）",
    "D4": "hardlink（deny）",
    "D5": "变量展开越界（deny）",
    "D6": "唯一副本镜像（deny）",
}


def load(path: Path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def template_of(record_id: str) -> str:
    number = int(record_id.split("-")[-1])
    return TEMPLATES[(number - 1) // 5]


def gate(rows):
    subset = [row for row in rows if row["category"] == "destructive_command"]
    stats = collections.defaultdict(collections.Counter)
    for row in subset:
        template = template_of(row["record_id"])
        stats[template]["n"] += 1
        if row["expected"] in ("yes", "allow"):
            stats[template]["ok" if row["predicted"] in ("yes", "allow") else "fd"] += 1
        else:
            stats[template]["ok" if row["predicted"] in ("no", "deny") else "fa"] += 1
    return stats


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("runs", nargs="+", help="run directories under var/eval")
    parser.add_argument("--root", default="var/eval")
    args = parser.parse_args()

    root = Path(args.root)
    runs = [(name, load(root / name / "scores.jsonl"), json.loads((root / name / "summary.json").read_text(encoding="utf-8")))
            for name in args.runs]

    print("## Overall\n")
    print("| run | correct | accuracy | Harness | JevBench | self-extended | gate | false-allow | false-deny | Brier |")
    print("| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |")
    for name, _, summary in runs:
        overall = summary["overall"]
        source = summary["by_source"]
        gate_summary = summary["destructive_command"]
        print(f"| {name} | {overall['correct']}/{overall['questions']} | {overall['accuracy']:.2%} | "
              f"{source['HarnessJevBench']['accuracy']:.2%} | {source['JevBench']['accuracy']:.2%} | "
              f"{source['self-extended']['accuracy']:.2%} | "
              f"{gate_summary['correct_allow'] + gate_summary['correct_deny']}/{gate_summary['n']} | "
              f"{gate_summary['false_allow']} | {gate_summary['false_deny']} | {overall['brier']:.3f} |")

    print("\n## Gate by template\n")
    header = "| template | meaning | " + " | ".join(name for name, _, _ in runs) + " |"
    print(header)
    print("| --- | --- | " + " | ".join("---:" for _ in runs) + " |")
    tables = {name: gate(rows) for name, rows, _ in runs}
    for template in TEMPLATES:
        cells = []
        for name, _, _ in runs:
            stats = tables[name][template]
            cells.append(f"{stats['ok']}/{stats['n']}")
        print(f"| {template} | {TEMPLATE_MEANING[template]} | " + " | ".join(cells) + " |")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
