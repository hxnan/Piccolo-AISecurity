#!/usr/bin/env python3
"""Validate the v4 training set and its policy-free hard-deletion source."""
from __future__ import annotations

import hashlib
import json
import unittest
from pathlib import Path

SECURITY = Path(__file__).resolve().parents[1]
TRAIN = SECURITY / "training" / "ais_security_train_v4.jsonl"
MANIFEST = SECURITY / "training" / "ais_security_train_v4.manifest.json"
HARD = SECURITY / "training" / "policy_free_deletion_v4.jsonl"


def load(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


class TrainingV4Test(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows = load(TRAIN)
        cls.manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        cls.hard = load(HARD)

    def test_counts(self):
        self.assertEqual(len(self.rows), 716)
        self.assertEqual(self.manifest["counts"]["by_split"], {"dev": 183, "train": 533})
        self.assertEqual(len(self.hard), 240)
        labels = [row["labels"]["decision"]["value"] for row in self.hard]
        self.assertEqual(labels.count(True), 120)
        self.assertEqual(labels.count(False), 120)

    def test_hard_source_is_policy_free(self):
        forbidden = {"review_policy", "review_rules", "evidence", "mutation_scope",
                     "protected_paths", "empty", "disposable", "legal_hold",
                     "only_copy", "protected", "dry_run_targets"}
        for row in self.hard:
            self.assertEqual(set(row["state"]), {"task", "shell", "cwd", "command", "environment"})
            text = json.dumps(row["state"], ensure_ascii=False)
            for key in forbidden:
                self.assertNotIn(f'"{key}"', text, row["id"])

    def test_ids_and_manifest_hash(self):
        self.assertEqual(hashlib.sha256(TRAIN.read_bytes()).hexdigest(), self.manifest["dataset_sha256"])
        ids = [row["id"] for row in self.rows]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(hashlib.sha256(HARD.read_bytes()).hexdigest(), self.manifest["hard_sha256"])

    def test_leakage_is_reported(self):
        report = self.manifest["leakage"]
        self.assertEqual(report["rejected"], [])
        self.assertLessEqual(report["max_command_lcs"], 60)
        self.assertTrue(report["template_overlap"])
        self.assertLess(report["max_jaccard_v3"], 1.0)


if __name__ == "__main__":
    unittest.main()
