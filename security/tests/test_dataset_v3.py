#!/usr/bin/env python3
"""Validate the policy-free v3 AISecurity set."""
from __future__ import annotations

import hashlib
import json
import sys
import unittest
from pathlib import Path

TESTS = Path(__file__).resolve().parent
SECURITY = TESTS.parent
sys.path.insert(0, str(SECURITY))

DATASET = SECURITY / "ais_security_v3.jsonl"
MANIFEST = SECURITY / "ais_security_v3.manifest.json"
HARD = SECURITY / "extended" / "deletion_guard_v3.jsonl"
FORBIDDEN = {
    "review_policy", "review_rules", "evidence", "mutation_scope", "protected_paths",
    "empty", "disposable", "legal_hold", "only_copy", "protected",
    "dry_run_targets", "target_kind", "target_exists",
}


def load_jsonl(path: Path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


class DatasetV3Test(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.bytes = DATASET.read_bytes()
        cls.rows = load_jsonl(DATASET)
        cls.manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        cls.hard = [row for row in cls.rows if row["category"] == "destructive_command"]

    def test_hash_and_counts(self):
        self.assertEqual(hashlib.sha256(self.bytes).hexdigest(), self.manifest["dataset_sha256"])
        self.assertEqual(len(self.rows), 255)
        self.assertEqual(self.manifest["counts"]["questions"], 263)

    def test_hard_set_is_policy_free(self):
        self.assertEqual(len(self.hard), 60)
        labels = [row["labels"]["decision"]["value"] for row in self.hard]
        self.assertEqual(labels.count(True), 30)
        self.assertEqual(labels.count(False), 30)
        for row in self.hard:
            self.assertEqual(set(row["state"]), {"task", "shell", "cwd", "command", "environment"})
            text = json.dumps(row["state"], ensure_ascii=False)
            for key in FORBIDDEN:
                self.assertNotIn(f'"{key}"', text, row["id"])

    def test_hard_ids_and_revision(self):
        v1_ids = {row["id"] for row in load_jsonl(SECURITY / "ais_security_v1.jsonl")}
        digest = hashlib.sha256(HARD.read_bytes()).hexdigest()
        for row in self.hard:
            self.assertNotIn(row["id"], v1_ids)
            self.assertTrue(row["id"].startswith("ais-x-del3-"))
            self.assertEqual(row["source"]["benchmark"], "self-extended")
            self.assertEqual(row["source"]["revision"], digest)

    def test_labels(self):
        for row in self.rows:
            for qid, question in row["questions"].items():
                value = row["labels"][qid]["value"]
                if question["type"] == "noul":
                    self.assertTrue(isinstance(value, bool) or
                                    (isinstance(value, str) and value.lower() in ("yes", "no")), row["id"])

    def test_leakage(self):
        report = self.manifest["leakage"]
        self.assertEqual(report["rejected"], [])
        self.assertLessEqual(report["max_jaccard_v1"], 0.25)
        self.assertLessEqual(report["max_jaccard_train"], 0.25)
        self.assertLessEqual(report["max_command_lcs"], 60)


if __name__ == "__main__":
    unittest.main()
