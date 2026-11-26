#!/usr/bin/env python3
"""Validate the first-version generalisation training set."""
from __future__ import annotations

import hashlib
import json
import sys
import unittest
from pathlib import Path

TESTS = Path(__file__).resolve().parent
SECURITY = TESTS.parent
sys.path.insert(0, str(SECURITY))

import build_training_set  # noqa: E402

TRAINING = SECURITY / "training"
DATASET = TRAINING / "ais_security_train_v1.jsonl"
MANIFEST = TRAINING / "ais_security_train_v1.manifest.json"


def load_jsonl(path: Path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def option_keys(question: dict) -> list:
    if question["type"] == "noul":
        return ["yes", "no"]
    if question["type"] == "score":
        return [str(i) for i in range(len(question["criteria"]))]
    return [str(k) for k in (question.get("option_order") or question["criteria"])]


class TrainingSetTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.bytes = DATASET.read_bytes()
        cls.rows = load_jsonl(DATASET)
        cls.manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))

    def test_manifest_hash_and_counts(self):
        self.assertEqual(hashlib.sha256(self.bytes).hexdigest(), self.manifest["dataset_sha256"])
        self.assertEqual(len(self.rows), self.manifest["counts"]["records"])
        self.assertEqual(len(self.rows), 596)
        self.assertEqual(self.manifest["counts"]["by_split"], {"dev": 155, "train": 441})

    def test_ids_are_unique(self):
        ids = [row["id"] for row in self.rows]
        self.assertEqual(len(ids), len(set(ids)))

    def test_labels_address_the_candidates(self):
        for row in self.rows:
            question = row["questions"]["decision"]
            value = row["labels"]["decision"]["value"]
            if question["type"] == "noul":
                self.assertIsInstance(value, bool, row["id"])
            else:
                self.assertIn(str(value), option_keys(question), row["id"])

    def test_no_label_leakage_in_state(self):
        banned = ("expected", "label", "ground_truth", "answer_key", "target")
        for row in self.rows:
            if isinstance(row["state"], dict):
                for key in banned:
                    self.assertNotIn(key, row["state"], row["id"])

    def test_split_is_by_family(self):
        seen = {}
        for row in self.rows:
            family = row["family"]
            self.assertIn(row["split"], ("train", "dev"))
            self.assertEqual(seen.setdefault(family, row["split"]), row["split"], family)

    def test_source_is_generated(self):
        for row in self.rows:
            self.assertEqual(row["source"]["benchmark"], "self-generated")
            self.assertEqual(row["source"]["license"], "Apache-2.0")

    def test_no_eval_markers(self):
        text = self.bytes.decode("utf-8").lower()
        for marker in build_training_set.BLOCKLIST:
            self.assertNotIn(marker, text, marker)

    def test_categories_are_covered(self):
        categories = {row["category"] for row in self.rows}
        self.assertEqual(
            categories,
            {
                "destructive_command",
                "authorization",
                "prompt_injection",
                "data_egress_privacy",
                "access_consent",
                "state_ambiguity_retry",
                "context_audit",
                "input_validation",
                "action_risk_gate",
            },
        )

    def test_leakage_report_is_clean(self):
        report = self.manifest["leakage"]
        self.assertEqual(report["rejected_count"], 0)
        self.assertLessEqual(report["max_jaccard"], 0.25)
        self.assertLessEqual(report["max_command_lcs"], 60)


if __name__ == "__main__":
    unittest.main()
