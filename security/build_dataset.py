#!/usr/bin/env python3
"""Build the Piccolo AISecurity evaluation set from pinned public benchmarks.

The builder is deterministic. It reads the same cached revisions that
``evaluation/reproduce.py`` prepares, keeps hard labels only, and writes one
JSONL record per source record plus a manifest with counts and a content hash.

Inclusion is deny-by-default and reviewable:

* HarnessJevBench is included by scenario, because the upstream scenario name
  describes the decision's purpose. Soft-only questions are dropped.
* JevBench Public has no security family, so items are included one by one
  after review. Every selected id is listed with a short rationale.
* Authored destructive-command cases live in ``extended/`` and are marked
  ``source.benchmark = self-extended`` with the file hash as their revision.

Usage:
    python evaluation/reproduce.py --base-url http://127.0.0.1:18604 \
        --model Piccolo-0.8B-VL --benchmarks harness jevbench --prepare-only
    python security/build_dataset.py
    python security/build_dataset.py --check
"""
from __future__ import annotations

import argparse
import collections
import hashlib
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
SOURCES = json.loads((HERE / "sources.json").read_text(encoding="utf-8"))
DATASET_NAME = "ais-security-v1"

# HarnessJevBench scenario -> AISecurity category. Scenario-level inclusion is
# deliberate: every record in a selected scenario asks for a security control
# decision, regardless of how the state is worded.
HARNESS_CATEGORIES = {
    "tool_permission": "authorization",
    "tool_call_review": "action_safety",
    "argument_validation": "input_validation",
    "browser_action": "ui_action_safety",
    "browser_confirmation": "user_consent",
    "privacy_release": "privacy_disclosure",
    "secret_egress": "data_egress",
    "injection_boundary": "prompt_injection",
    "safety_gate": "action_risk_gate",
    "memory_write": "data_persistence",
    "delegation": "privilege_scoping",
    "subagent_dispatch": "privilege_scoping",
    "context_compression": "context_integrity",
    "context_retention": "audit_integrity",
    "version_conflict": "state_integrity",
    "cache_validity": "state_integrity",
    "retry_or_escalate": "retry_safety",
    "clarification_abstention": "ambiguity_safety",
}

# Reviewed and left out. Recorded in the manifest so the scope stays explicit.
HARNESS_EXCLUDED = {
    "budget_allocation": "resource planning, not a security control",
    "completion_verification": "completion checking, not a security control",
    "concurrency_transaction": "transaction consistency, not a security control",
    "model_routing": "model routing, not a security control",
    "plan_progress": "plan progress, not a security control",
    "reasoning_budget": "reasoning budget, not a security control",
    "retrieval_evidence": "evidence sufficiency, not a security control",
    "retry_recovery": "retry recovery, not a security control",
    "termination_evidence": "termination evidence, not a security control",
    "tool_selection": "tool choice, not a security control",
    "trajectory_progress": "trajectory progress, not a security control",
}

# JevBench Public items selected after reading the public splits. Keys are
# upstream ids; values are (category, rationale shown in the manifest).
JEVBENCH_SELECTION = {
    "hard-sol-a-adversarial-01": (
        "prompt_injection",
        "uploaded file spoofs an approval; access must follow trusted metadata",
    ),
    "hard-sol-a-adversarial-06": (
        "prompt_injection",
        "HTML comment injects a sponsorship claim; user-controlled content is not metadata",
    ),
    "hard-sol-a-adversarial-07": (
        "prompt_injection",
        "text layer in a scanned contract injects a deletion directive",
    ),
    "hard-sol-a-adversarial-08": (
        "prompt_injection",
        "hidden resume text injects a score override",
    ),
    "hard-sol-a-adversarial-09": (
        "prompt_injection",
        "diagnostic filename claims an outage; priority follows monitoring",
    ),
    "hard-sol-a-adversarial-11": (
        "prompt_injection",
        "narrative injects an authoritative router notice",
    ),
    "original-policy-05-0": (
        "access_control",
        "suspension overrides own-team file access",
    ),
    "original-policy-05-1": (
        "access_control",
        "suspended employee requests own-team file",
    ),
    "hard-opus-b-ambiguous-09": (
        "security_operations",
        "SOC impossible-travel triage with MFA and device evidence",
    ),
    "hard-opus-c-long_policy-02": (
        "privacy_compliance",
        "GDPR erasure request versus transaction-record retention",
    ),
    "hard-sol-a-trap-05": (
        "access_control",
        "whether an address-override exception was actually authorized",
    ),
    "hard-sol-b-long_policy-02": (
        "data_access",
        "customer export limited by direct-identifier and aggregate rules",
    ),
    "hard-sol-b-long_policy-05": (
        "privacy_compliance",
        "deletion schedule conflicts with a legal hold",
    ),
}

# Reviewed but left out to hit the agreed 13-item budget; kept here so the
# triage decision is reproducible and can be revisited.
JEVBENCH_DROPPED = {
    "hard-opus-b-ambiguous-10": "recipient disambiguation is data-loss prevention, weaker security signal",
    "hard-opus-c-long_policy-08": "incident severity grading is closer to operations than security",
    "hard-sol-a-multi_hop-02": "security routing is already covered by the SOC triage item",
    "hard-sol-a-multi_hop-10": "PII access exception overlaps the export-standard item",
    "hard-sol-a-multi_hop-12": "identity verification is a single narrow case",
    "hard-sol-b-routing_hard-02": "fraud routing overlaps security operations coverage",
    "hard-sol-b-routing_hard-09": "repository authorization overlaps the access-control items",
}

# Authored records live next to this script so they can be reviewed and
# diffed like any other data. They are not derived from an upstream benchmark.
EXTENDED_PATH = HERE / "extended" / "deletion_guard_v1.jsonl"
EXTENDED_CATEGORY = "destructive_command"

JEVBENCH_EXCLUDED_FAMILIES = {
    "intent": "intent classification",
    "fact": "factual reading",
    "extraction": "field extraction",
    "tool_selection": "tool choice",
    "adequacy": "answer adequacy",
    "judge_hard": "answer-quality judging",
    "ordinal": "incident impact scale (availability, not security)",
    "probability": "probabilistic forecasting",
    "temporal_numeric": "date and threshold arithmetic",
    "tradeoff": "policy precedence in business workflows",
    "trap": "careful reading of ordinary business rules",
    "ambiguous": "evidence-quality ambiguity, except selected security cases",
    "multi_hop": "document reasoning, except selected security cases",
    "long_policy": "long policy reasoning, except selected privacy/security cases",
    "policy": "business policy compliance, except selected access-control cases",
    "routing": "specialist routing",
    "routing_hard": "specialist routing, except selected security cases",
    "adversarial": "none: all public adversarial items are included",
}

ALLOWED_QUESTION_TYPES = ("noul", "choice", "score")


def read_jsonl(path: Path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def pinned_repo(cache: Path, name: str) -> Path:
    spec = SOURCES[name]
    path = cache / name / spec["revision"]
    if not path.is_dir():
        raise SystemExit(
            "missing cached source: %s\n"
            "prepare it first: python evaluation/reproduce.py "
            "--base-url http://127.0.0.1:18604 --model Piccolo-0.8B-VL "
            "--benchmarks harness jevbench --prepare-only" % path
        )
    try:
        head = subprocess.check_output(
            ["git", "-C", str(path), "rev-parse", "HEAD"], text=True
        ).strip()
    except (OSError, subprocess.CalledProcessError) as error:
        raise SystemExit(f"cannot read revision of {path}: {error}") from error
    if head != spec["revision"]:
        raise SystemExit(f"{name}: cached revision {head} != pinned {spec['revision']}")
    return path


def option_keys(question: dict) -> list:
    if question["type"] == "score":
        return [str(i) for i in range(len(question["criteria"]))]
    return [str(key) for key in question.get("option_order") or question["criteria"]]


def validate_question(record_id: str, qid: str, question: dict, label: dict) -> None:
    if question.get("type") not in ALLOWED_QUESTION_TYPES:
        raise SystemExit(f"{record_id}/{qid}: unsupported question type")
    if label.get("label_type") != "hard":
        raise SystemExit(f"{record_id}/{qid}: expected a hard label")
    value = label.get("value")
    if question["type"] == "noul":
        if isinstance(value, bool):
            return
        if isinstance(value, str) and value.lower() in ("yes", "no"):
            return
        raise SystemExit(f"{record_id}/{qid}: noul label must be bool or yes/no")
    if str(value) not in option_keys(question):
        raise SystemExit(f"{record_id}/{qid}: label {value!r} not in option keys")


def harness_items(cache: Path):
    spec = SOURCES["harness"]
    repo = pinned_repo(cache, "harness")
    records = read_jsonl(repo / spec["record_path"])
    items = []
    unselected = collections.Counter()
    soft_only = collections.Counter()
    for record in records:
        scenario = record.get("metadata", {}).get("scenario")
        category = HARNESS_CATEGORIES.get(scenario)
        if category is None:
            unselected[scenario] += 1
            continue
        labels = {
            qid: label
            for qid, label in record["labels"].items()
            if label.get("label_type") == "hard"
        }
        if not labels:
            soft_only[scenario] += 1
            continue
        questions = {}
        for qid in labels:
            if qid not in record["questions"]:
                raise SystemExit(f"{record['id']}: label without question {qid}")
            question = record["questions"][qid]
            validate_question(record["id"], qid, question, labels[qid])
            questions[qid] = question
        items.append(
            {
                "id": "ais-h-" + record["id"],
                "category": category,
                "source": {
                    "benchmark": "HarnessJevBench",
                    "source_id": record["id"],
                    "revision": spec["revision"],
                    "split": "hard",
                    "scenario": scenario,
                    "license": spec["data_license"],
                },
                "state": record["state"],
                "questions": questions,
                "labels": {
                    qid: {"label_type": "hard", "value": labels[qid]["value"]}
                    for qid in labels
                },
            }
        )
    return items, unselected, soft_only


def jevbench_items(cache: Path):
    spec = SOURCES["jevbench"]
    repo = pinned_repo(cache, "jevbench")
    by_id = {}
    split_of = {}
    for relative in spec["record_paths"]:
        split = Path(relative).stem
        for row in read_jsonl(repo / relative):
            if row["id"] in by_id:
                raise SystemExit(f"duplicate JevBench id: {row['id']}")
            by_id[row["id"]] = row
            split_of[row["id"]] = split
    missing = sorted(set(JEVBENCH_SELECTION) - set(by_id))
    if missing:
        raise SystemExit("selected ids missing from JevBench: " + ", ".join(missing))
    items = []
    for source_id, (category, _) in JEVBENCH_SELECTION.items():
        row = by_id[source_id]
        question = row["question"]
        label = {"label_type": "hard", "value": row.get("expected")}
        if label["value"] is None:
            raise SystemExit(f"{source_id}: selected item has no expected value")
        validate_question(source_id, "decision", question, label)
        items.append(
            {
                "id": "ais-j-" + source_id,
                "category": category,
                "source": {
                    "benchmark": "JevBench",
                    "source_id": source_id,
                    "revision": spec["revision"],
                    "split": split_of[source_id],
                    "visibility": row.get("split"),
                    "family": row.get("family"),
                    "license": row.get("provenance", {}).get("license")
                    or spec["data_license"],
                },
                "state": row["state"],
                "questions": {"decision": question},
                "labels": {"decision": label},
            }
        )
    return items, by_id


def validate_items(items) -> None:
    seen = set()
    for item in items:
        if item["id"] in seen:
            raise SystemExit(f"duplicate record id: {item['id']}")
        seen.add(item["id"])
        if not item["questions"]:
            raise SystemExit(f"{item['id']}: no questions")
        if set(item["questions"]) != set(item["labels"]):
            raise SystemExit(f"{item['id']}: question/label keys differ")
        for qid, question in item["questions"].items():
            validate_question(item["id"], qid, question, item["labels"][qid])


def extended_items():
    """Load authored destructive-command cases and pin them by file hash."""
    if not EXTENDED_PATH.is_file():
        raise SystemExit(f"missing authored records: {EXTENDED_PATH}")
    digest = hashlib.sha256(EXTENDED_PATH.read_bytes()).hexdigest()
    rows = read_jsonl(EXTENDED_PATH)
    languages = collections.Counter(row.get("language") for row in rows)
    if languages != {"zh": 15, "en": 15}:
        raise SystemExit(f"extended set must be 15 zh + 15 en, got {dict(languages)}")
    difficulties = sorted(row.get("difficulty") for row in rows if row.get("language") == "zh")
    if difficulties != list(range(1, 16)):
        raise SystemExit(f"zh cases must use difficulty 1..15, got {difficulties}")
    difficulties = sorted(row.get("difficulty") for row in rows if row.get("language") == "en")
    if difficulties != list(range(1, 16)):
        raise SystemExit(f"en cases must use difficulty 1..15, got {difficulties}")
    items = []
    seen = set()
    for row in rows:
        if row["id"] in seen:
            raise SystemExit(f"duplicate authored id: {row['id']}")
        seen.add(row["id"])
        if set(row["questions"]) != {"decision"}:
            raise SystemExit(f"{row['id']}: expected a single decision question")
        if row["difficulty"] >= 11 and len(row["state"]["proposed_command"]) < 300:
            raise SystemExit(
                f"{row['id']}: difficulty 11+ requires a 300+ character compound command"
            )
        validate_question(row["id"], "decision", row["questions"]["decision"], row["labels"]["decision"])
        items.append(
            {
                "id": "ais-x-" + row["id"],
                "category": EXTENDED_CATEGORY,
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
    return items, digest, rows


def serialise(items) -> bytes:
    lines = [json.dumps(item, ensure_ascii=False, separators=(",", ":")) for item in items]
    return ("\n".join(lines) + "\n").encode("utf-8")


def build_manifest(items, dataset_bytes, harness_meta, jevbench_meta, extended_meta) -> dict:
    by_benchmark = collections.Counter()
    by_category = collections.Counter()
    by_scenario = collections.Counter()
    by_family = collections.Counter()
    by_type = collections.Counter()
    for item in items:
        source = item["source"]
        by_benchmark[source["benchmark"]] += 1
        by_category[item["category"]] += 1
        if source["benchmark"] == "HarnessJevBench":
            by_scenario[source["scenario"]] += 1
        elif source["benchmark"] == "JevBench":
            by_family[source["family"]] += 1
        for question in item["questions"].values():
            by_type[question["type"]] += 1

    unselected, soft_only = harness_meta[1], harness_meta[2]
    _, jevbench_rows = jevbench_meta
    ext_items, ext_sha, ext_rows = extended_meta
    family_totals = collections.Counter(row.get("family") for row in jevbench_rows.values())
    selected_by_family = collections.Counter(
        item["source"]["family"] for item in items if item["source"]["benchmark"] == "JevBench"
    )
    excluded_counts = {
        family: family_totals[family] - selected_by_family.get(family, 0)
        for family in sorted(family_totals)
        if family_totals[family] - selected_by_family.get(family, 0)
    }
    labels = collections.Counter(
        "true" if item["labels"]["decision"]["value"] else "false" for item in ext_items
    )

    return {
        "name": DATASET_NAME,
        "description": (
            "Hard-label AI security decisions merged from HarnessJevBench and "
            "JevBench Public, plus authored destructive-command cases. Native "
            "state/questions, expected labels, and an explicit source per record."
        ),
        "dataset": "ais_security_v1.jsonl",
        "dataset_sha256": hashlib.sha256(dataset_bytes).hexdigest(),
        "counts": {
            "records": len(items),
            "questions": sum(len(item["questions"]) for item in items),
            "by_benchmark": dict(sorted(by_benchmark.items())),
            "by_category": dict(sorted(by_category.items())),
            "harness_by_scenario": dict(sorted(by_scenario.items())),
            "jevbench_by_family": dict(sorted(by_family.items())),
            "by_question_type": dict(sorted(by_type.items())),
            "extended_by_language": dict(
                sorted(collections.Counter(row["language"] for row in ext_rows).items())
            ),
            "extended_by_difficulty": dict(
                sorted(collections.Counter(row["difficulty"] for row in ext_rows).items())
            ),
        },
        "selection": {
            "labels": "hard only; upstream soft probability views are excluded",
            "harness": {
                "rule": "scenario-level inclusion; records with no hard question are dropped",
                "included_scenarios": dict(sorted(HARNESS_CATEGORIES.items())),
                "excluded_scenarios": dict(sorted(HARNESS_EXCLUDED.items())),
                "unselected_records": dict(sorted((k or "unknown", v) for k, v in unselected.items())),
                "soft_only_records_dropped": dict(sorted((k or "unknown", v) for k, v in soft_only.items())),
            },
            "jevbench": {
                "rule": "item-level review of the public original/easy/hard splits",
                "included_ids": {key: value[0] for key, value in JEVBENCH_SELECTION.items()},
                "included_rationale": {key: value[1] for key, value in JEVBENCH_SELECTION.items()},
                "dropped_ids": dict(sorted(JEVBENCH_DROPPED.items())),
                "excluded_families": {
                    family: reason
                    for family, reason in JEVBENCH_EXCLUDED_FAMILIES.items()
                    if family != "adversarial"
                },
                "excluded_records_by_family": excluded_counts,
            },
            "extended": {
                "rule": "authored for this repository; not derived from an upstream benchmark",
                "file": EXTENDED_PATH.name,
                "sha256": ext_sha,
                "category": EXTENDED_CATEGORY,
                "records": len(ext_items),
                "languages": dict(sorted(collections.Counter(row["language"] for row in ext_rows).items())),
                "difficulty_order": "1 = simplest task and command, 15 = longest compound command",
                "label_balance": dict(sorted(labels.items())),
                "decision": "binary auto-approval gate for cmd.exe deletion commands built around cd .. && del patterns",
                "hard_tier": "difficulty 11-15 use 300+ character command chains across multiple directories and include users who wave the risk away",
            },
        },
        "sources": SOURCES,
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--cache",
        type=Path,
        default=ROOT / "var" / "evaluation" / "cache",
        help="cache populated by evaluation/reproduce.py --prepare-only",
    )
    parser.add_argument("--dataset", type=Path, default=HERE / "ais_security_v1.jsonl")
    parser.add_argument(
        "--manifest", type=Path, default=HERE / "ais_security_v1.manifest.json"
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="verify that the committed dataset and manifest match a fresh build",
    )
    args = parser.parse_args(argv)

    cache = args.cache.resolve()
    harness_meta = harness_items(cache)
    jevbench_meta = jevbench_items(cache)
    extended_meta = extended_items()
    items = harness_meta[0] + jevbench_meta[0] + extended_meta[0]
    validate_items(items)
    dataset_bytes = serialise(items)
    manifest = build_manifest(items, dataset_bytes, harness_meta, jevbench_meta, extended_meta)
    manifest_bytes = (
        json.dumps(manifest, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
    ).encode("utf-8")

    if args.check:
        problems = []
        for path, expected in ((args.dataset, dataset_bytes), (args.manifest, manifest_bytes)):
            if not path.is_file():
                problems.append(f"missing {path}")
            elif path.read_bytes() != expected:
                problems.append(f"stale {path}")
        if problems:
            print("\n".join(problems), file=sys.stderr)
            return 1
        print(f"ok: {len(items)} records, {manifest['counts']['questions']} questions")
        return 0

    args.dataset.parent.mkdir(parents=True, exist_ok=True)
    args.manifest.parent.mkdir(parents=True, exist_ok=True)
    args.dataset.write_bytes(dataset_bytes)
    args.manifest.write_bytes(manifest_bytes)
    print(
        f"wrote {args.dataset} ({len(items)} records, "
        f"{manifest['counts']['questions']} questions) and {args.manifest}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
