#!/usr/bin/env python3
"""Validate the committed AISecurity dataset against its manifest.

Run from the repository root:

    python security/tests/test_dataset.py -v
"""
from __future__ import annotations

import hashlib
import json
import sys
import unittest
from pathlib import Path

TESTS = Path(__file__).resolve().parent
SECURITY = TESTS.parent
ROOT = SECURITY.parent
sys.path.insert(0, str(SECURITY))

import build_dataset  # noqa: E402

DATASET_NAME = build_dataset.DATASET_NAME.replace("-", "_")
DATASET = SECURITY / (DATASET_NAME + ".jsonl")
MANIFEST = SECURITY / (DATASET_NAME + ".manifest.json")


def load_jsonl(path: Path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


class DatasetTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.bytes = DATASET.read_bytes()
        cls.rows = load_jsonl(DATASET)
        cls.manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))

    def test_manifest_hash_and_counts(self):
        self.assertEqual(hashlib.sha256(self.bytes).hexdigest(), self.manifest["dataset_sha256"])
        self.assertEqual(len(self.rows), self.manifest["counts"]["records"])
        self.assertEqual(
            sum(len(row["questions"]) for row in self.rows),
            self.manifest["counts"]["questions"],
        )

    def test_ids_are_unique(self):
        ids = [row["id"] for row in self.rows]
        self.assertEqual(len(ids), len(set(ids)))

    def test_source_revisions_are_pinned(self):
        for row in self.rows:
            source = row["source"]
            if source["benchmark"] == "self-extended":
                continue
            key = "harness" if source["benchmark"] == "HarnessJevBench" else "jevbench"
            self.assertEqual(source["revision"], build_dataset.SOURCES[key]["revision"])

    def test_labels_are_hard_and_addressable(self):
        for row in self.rows:
            self.assertEqual(set(row["questions"]), set(row["labels"]))
            for qid, label in row["labels"].items():
                self.assertEqual(label["label_type"], "hard", row["id"])
                question = row["questions"][qid]
                self.assertIn(question["type"], build_dataset.ALLOWED_QUESTION_TYPES)
                value = label["value"]
                if question["type"] == "noul":
                    self.assertTrue(
                        isinstance(value, bool)
                        or (isinstance(value, str) and value.lower() in ("yes", "no")),
                        f"{row['id']}/{qid}",
                    )
                else:
                    self.assertIn(str(value), build_dataset.option_keys(question), f"{row['id']}/{qid}")

    def test_no_label_leakage_in_state(self):
        banned = ("expected", "label", "ground_truth", "answer_key")
        for row in self.rows:
            if isinstance(row["state"], dict):
                for key in banned:
                    self.assertNotIn(key, row["state"], row["id"])

    def test_categories_are_declared(self):
        declared = set(build_dataset.HARNESS_CATEGORIES.values()) | {
            category for category, _ in build_dataset.JEVBENCH_SELECTION.values()
        } | {build_dataset.EXTENDED_CATEGORY}
        for row in self.rows:
            self.assertIn(row["category"], declared, row["id"])

    def test_extended_set_is_complete(self):
        extended = [row for row in self.rows if row["source"]["benchmark"] == "self-extended"]
        self.assertEqual(len(extended), 30)
        self.assertEqual(
            {row["source"]["language"] for row in extended}, {"zh", "en"}
        )
        for language in ("zh", "en"):
            subset = [row for row in extended if row["source"]["language"] == language]
            self.assertEqual(len(subset), 15)
            self.assertEqual(
                sorted(row["source"]["difficulty"] for row in subset), list(range(1, 16))
            )
        labels = [row["labels"]["decision"]["value"] for row in extended]
        self.assertEqual(labels.count(True), 14)
        self.assertEqual(labels.count(False), 16)
        for row in extended:
            if row["source"]["difficulty"] >= 11:
                self.assertGreaterEqual(
                    len(row["state"]["proposed_command"]), 300, row["id"]
                )
        digest = hashlib.sha256(build_dataset.EXTENDED_PATH.read_bytes()).hexdigest()
        for row in extended:
            self.assertEqual(row["source"]["revision"], digest)

    def test_jevbench_selection_is_complete(self):
        selected = {
            row["source"]["source_id"]
            for row in self.rows
            if row["source"]["benchmark"] == "JevBench"
        }
        self.assertEqual(selected, set(build_dataset.JEVBENCH_SELECTION))

    def test_manifest_selection_matches_builder(self):
        selection = self.manifest["selection"]
        self.assertEqual(
            selection["harness"]["included_scenarios"],
            dict(sorted(build_dataset.HARNESS_CATEGORIES.items())),
        )
        self.assertEqual(
            selection["jevbench"]["included_ids"],
            {key: value[0] for key, value in build_dataset.JEVBENCH_SELECTION.items()},
        )

    def test_dataset_can_be_rebuilt(self):
        """The build path used by CI: rebuild from cache and compare bytes."""
        cache = ROOT / "var" / "evaluation" / "cache"
        if not (cache / "harness").is_dir():
            self.skipTest("pinned sources are not cached; run evaluation/reproduce.py --prepare-only")
        harness_meta = build_dataset.harness_items(cache.resolve())
        jevbench_meta = build_dataset.jevbench_items(cache.resolve())
        extended_meta = build_dataset.extended_items()
        items = harness_meta[0] + jevbench_meta[0] + extended_meta[0]
        build_dataset.validate_items(items)
        self.assertEqual(build_dataset.serialise(items), self.bytes)


if __name__ == "__main__":
    unittest.main()
