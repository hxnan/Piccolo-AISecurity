#!/usr/bin/env python3
"""Validate the v5 eval set and v5 training set."""
from __future__ import annotations

import hashlib
import json
import unittest
from pathlib import Path

SECURITY = Path(__file__).resolve().parents[1]
V5 = SECURITY / "ais_security_v5.jsonl"
V5_MANIFEST = SECURITY / "ais_security_v5.manifest.json"
HARD5 = SECURITY / "extended" / "deletion_guard_v5.jsonl"
TRAIN5 = SECURITY / "training" / "ais_security_train_v5.jsonl"
TRAIN5_MANIFEST = SECURITY / "training" / "ais_security_train_v5.manifest.json"
FORBIDDEN = {"review_policy", "review_rules", "evidence", "mutation_scope",
             "protected_paths", "empty", "disposable", "legal_hold", "only_copy",
             "protected", "dry_run_targets"}


def load(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


class V5Test(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows = load(V5)
        cls.manifest = json.loads(V5_MANIFEST.read_text(encoding="utf-8"))
        cls.hard = [row for row in cls.rows if row["category"] == "destructive_command"]

    def test_eval_counts_and_question_style(self):
        self.assertEqual(len(self.rows), 255)
        self.assertEqual(self.manifest["counts"]["questions"], 263)
        self.assertEqual(len(self.hard), 60)
        labels = [row["labels"]["decision"]["value"] for row in self.hard]
        self.assertEqual(labels.count("allow"), 30)
        self.assertEqual(labels.count("deny"), 30)
        for row in self.hard:
            q = row["questions"]["decision"]
            self.assertEqual(q["type"], "choice")
            self.assertEqual(q["option_order"], ["allow", "confirm", "deny"])
            self.assertEqual(set(q["criteria"]), {"allow", "confirm", "deny"})
            text = json.dumps(row["state"], ensure_ascii=False)
            for key in FORBIDDEN:
                self.assertNotIn(f'"{key}"', text, row["id"])

    def test_eval_hash(self):
        self.assertEqual(hashlib.sha256(V5.read_bytes()).hexdigest(), self.manifest["dataset_sha256"])

    def test_training_counts(self):
        train = load(TRAIN5)
        manifest = json.loads(TRAIN5_MANIFEST.read_text(encoding="utf-8"))
        self.assertEqual(len(train), 1489)
        self.assertEqual(manifest["counts"]["by_split"], {"dev": 203, "train": 1286})
        hard = [row for row in train if row["category"] == "destructive_command"]
        self.assertEqual(len(hard), 552)
        policy_free = [row for row in hard if row["id"].startswith("tr4-")]
        self.assertEqual(len(policy_free), 432)
        labels = [row["labels"]["decision"]["value"] for row in policy_free]
        self.assertEqual(labels.count("allow"), 216)
        self.assertEqual(labels.count("deny"), 216)
        for row in hard:
            question = row["questions"]["decision"]
            self.assertEqual(question["type"], "choice")
            self.assertEqual(question["option_order"], ["allow", "confirm", "deny"])
            text = json.dumps(question, ensure_ascii=False)
            self.assertNotIn("审查规则", text)
            self.assertNotIn("review rule", text)
            self.assertNotIn("自动放行", text)
            self.assertNotIn("auto-approved", text)

    def test_compact_variant(self):
        manifest = json.loads(TRAIN5_MANIFEST.read_text(encoding="utf-8"))
        compact = SECURITY / "training" / manifest["compact"]
        payload = compact.read_bytes()
        self.assertEqual(hashlib.sha256(payload).hexdigest(), manifest["compact_sha256"])
        rows = [json.loads(line) for line in payload.decode("utf-8").splitlines() if line.strip()]
        self.assertEqual(len(rows), 1088)
        self.assertEqual(len([row for row in rows if row["split"] == "train"]), 885)

    def test_training_ids_unique(self):
        ids = [row["id"] for row in load(TRAIN5)]
        self.assertEqual(len(ids), len(set(ids)))

    def test_open_source_cases_unchanged(self):
        """Only self-extended cases may be re-authored; imported benchmarks stay byte-identical."""
        v3 = {row["id"]: row for row in load(SECURITY / "ais_security_v3.jsonl")}
        external = [row for row in self.rows if row["source"]["benchmark"] != "self-extended"]
        self.assertEqual(len(external), 195)
        for row in external:
            self.assertIn(row["id"], v3)
            before = v3[row["id"]]
            for field in ("state", "questions", "labels"):
                self.assertEqual(
                    json.dumps(before[field], ensure_ascii=False, sort_keys=True),
                    json.dumps(row[field], ensure_ascii=False, sort_keys=True),
                    f"{row['id']}: {field} was modified",
                )

    def test_stage2_split(self):
        manifest = json.loads(TRAIN5_MANIFEST.read_text(encoding="utf-8"))
        stage2 = SECURITY / "training" / manifest["stage2"]
        payload = stage2.read_bytes()
        self.assertEqual(hashlib.sha256(payload).hexdigest(), manifest["stage2_sha256"])
        rows = [json.loads(line) for line in payload.decode("utf-8").splitlines() if line.strip()]
        self.assertEqual(len(rows), 240)
        import re
        dev = {re.search(r"tr4-([ad]\d{1,2})-", row["id"]).group(1) for row in rows if row["split"] == "dev"}
        train = {re.search(r"tr4-([ad]\d{1,2})-", row["id"]).group(1) for row in rows if row["split"] == "train"}
        self.assertEqual(dev, {"a3", "a6", "d7", "d10"})
        self.assertIn("d2", train)
        self.assertNotIn("d2", dev)


if __name__ == "__main__":
    unittest.main()
