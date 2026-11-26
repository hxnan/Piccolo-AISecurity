#!/usr/bin/env python3
"""Validate the v2 AISecurity set with the 60 hard deletion cases."""
from __future__ import annotations

import hashlib
import json
import sys
import unittest
from pathlib import Path

TESTS = Path(__file__).resolve().parent
SECURITY = TESTS.parent
sys.path.insert(0, str(SECURITY))

import build_dataset_v2  # noqa: E402

DATASET = SECURITY / "ais_security_v2.jsonl"
MANIFEST = SECURITY / "ais_security_v2.manifest.json"
HARD = SECURITY / "extended" / "deletion_guard_v2.jsonl"


def load_jsonl(path: Path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def option_keys(question):
    if question["type"] == "noul":
        return ["yes", "no"]
    if question["type"] == "score":
        return [str(i) for i in range(len(question["criteria"]))]
    return [str(k) for k in (question.get("option_order") or question["criteria"])]


class DatasetV2Test(unittest.TestCase):
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
        self.assertEqual(self.manifest["counts"]["by_source"],
                         {"HarnessJevBench": 182, "JevBench": 13, "self-extended": 60})

    def test_hard_set_shape(self):
        self.assertEqual(len(self.hard), 60)
        labels = [row["labels"]["decision"]["value"] for row in self.hard]
        self.assertEqual(labels.count(True), 30)
        self.assertEqual(labels.count(False), 30)
        languages = {lang: sum(1 for row in self.hard if row["source"]["language"] == lang)
                     for lang in ("zh", "en")}
        self.assertEqual(languages, {"zh": 36, "en": 24})
        digest = hashlib.sha256(HARD.read_bytes()).hexdigest()
        for row in self.hard:
            self.assertEqual(row["source"]["benchmark"], "self-extended")
            self.assertEqual(row["source"]["revision"], digest)

    def test_labels_address_candidates(self):
        for row in self.rows:
            for qid, question in row["questions"].items():
                value = row["labels"][qid]["value"]
                if question["type"] == "noul":
                    self.assertTrue(
                        isinstance(value, bool)
                        or (isinstance(value, str) and value.lower() in ("yes", "no")),
                        row["id"],
                    )
                else:
                    self.assertIn(str(value), option_keys(question), row["id"])

    def test_hard_ids_do_not_reuse_v1_easy_ids(self):
        v1_ids = {row["id"] for row in load_jsonl(SECURITY / "ais_security_v1.jsonl")}
        for row in self.hard:
            self.assertNotIn(row["id"], v1_ids)
            self.assertTrue(row["id"].startswith("ais-x-del2-"))

    def test_leakage_report(self):
        report = self.manifest["leakage"]
        self.assertEqual(report["rejected"], [])
        self.assertLessEqual(report["max_jaccard_v1"], 0.25)
        self.assertLessEqual(report["max_jaccard_train"], 0.25)
        self.assertLessEqual(report["max_command_lcs"], 60)

    def test_no_label_leakage_in_state(self):
        banned = ("expected", "label", "ground_truth", "answer_key")
        for row in self.rows:
            if isinstance(row["state"], dict):
                for key in banned:
                    self.assertNotIn(key, row["state"], row["id"])


if __name__ == "__main__":
    unittest.main()
