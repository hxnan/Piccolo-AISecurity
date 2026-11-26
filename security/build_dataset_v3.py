#!/usr/bin/env python3
"""Build the v3 AISecurity set: v1 non-destructive cases + 60 policy-free hard cases."""
from __future__ import annotations

import json
from pathlib import Path

import build_dataset_v2 as base

HERE = Path(__file__).resolve().parent
base.HARD = HERE / "extended" / "deletion_guard_v3.jsonl"
base.OUT = HERE / "ais_security_v3.jsonl"
base.MANIFEST = HERE / "ais_security_v3.manifest.json"


def main() -> int:
    code = base.main()
    manifest = json.loads(base.MANIFEST.read_text(encoding="utf-8"))
    manifest["name"] = "ais-security-v3"
    manifest["description"] = (
        "v1 non-destructive cases plus 60 policy-free hard destructive-command cases. "
        "The input contains only task context, shell, cwd, command and raw environment files; "
        "no review policy and no pre-computed evidence conclusions."
    )
    manifest["hard_set"] = "extended/deletion_guard_v3.jsonl"
    manifest["selection"] = {
        "rule": "v1 non-destructive records unchanged; 30 easy deletion cases replaced by 60 policy-free hard cases",
        "policy_free": True,
        "state_fields": ["task", "shell", "cwd", "command", "environment"],
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
        "no_policy": "review_policy, review_rules and evidence conclusions are absent from every state",
    }
    base.MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("patched manifest for v3")
    return code


if __name__ == "__main__":
    raise SystemExit(main())
