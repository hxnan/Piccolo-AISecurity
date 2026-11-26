#!/usr/bin/env python3
"""Offline checks for the scoring and response-validation helpers."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

TESTS = Path(__file__).resolve().parent
SECURITY = TESTS.parent
sys.path.insert(0, str(SECURITY))

import run_eval  # noqa: E402
import score_eval  # noqa: E402


def record(qtype, expected, criteria):
    return {
        "id": "ais-test",
        "category": "destructive_command",
        "source": {"benchmark": "self-extended", "language": "zh", "difficulty": 1},
        "state": "s",
        "questions": {
            "decision": {"type": qtype, "instructions": "i", "criteria": criteria}
        },
        "labels": {"decision": {"label_type": "hard", "value": expected}},
    }


def raw(answer, ok=True):
    return {"ok": ok, "status": 200, "seconds": 0.1, "answer": answer}


class ScoreTest(unittest.TestCase):
    def score(self, row, answer, ok=True):
        task = {"row": row, "question_id": "decision"}
        return score_eval.score_row(task, raw(answer, ok))

    def test_noul_expected_no(self):
        row = record("noul", False, {"false": "no", "true": "yes"})
        result = self.score(row, {"type": "noul", "noul": 0.8})
        self.assertTrue(result["valid"])
        self.assertEqual(result["predicted"], "yes")
        self.assertFalse(result["correct"])
        self.assertAlmostEqual(result["brier"], 0.64, places=6)

    def test_choice_expected_key(self):
        row = record("choice", "b", {"a": "A", "b": "B"})
        result = self.score(row, {"type": "choice", "probabilities": {"a": 0.3, "b": 0.7}})
        self.assertTrue(result["valid"])
        self.assertTrue(result["correct"])
        self.assertEqual(result["predicted"], "b")

    def test_score_level(self):
        row = record("score", 1, ["level 0", "level 1"])
        result = self.score(row, {"type": "score", "probabilities": {"0": 0.2, "1": 0.8}})
        self.assertTrue(result["valid"])
        self.assertTrue(result["correct"])

    def test_invalid_distribution(self):
        row = record("choice", "b", {"a": "A", "b": "B"})
        result = self.score(row, {"type": "choice", "probabilities": {"a": 0.9, "b": 0.9}})
        self.assertFalse(result["valid"])
        self.assertFalse(result["correct"])

    def test_missing_raw(self):
        row = record("noul", True, {"false": "no", "true": "yes"})
        task = {"row": row, "question_id": "decision"}
        result = score_eval.score_row(task, None)
        self.assertEqual(result["status"], "missing")
        self.assertFalse(result["correct"])

    def test_validate_answer(self):
        noul = {"type": "noul", "instructions": "i", "criteria": {"false": "n", "true": "y"}}
        run_eval.validate_answer({"type": "noul", "noul": 0.4}, noul)
        with self.assertRaises(ValueError):
            run_eval.validate_answer({"type": "noul", "noul": 1.4}, noul)
        choice = {"type": "choice", "instructions": "i", "criteria": {"a": "A", "b": "B"}}
        run_eval.validate_answer({"type": "choice", "probabilities": {"a": 0.4, "b": 0.6}}, choice)
        with self.assertRaises(ValueError):
            run_eval.validate_answer({"type": "choice", "probabilities": {"a": 1.0}}, choice)

    def test_confusion(self):
        rows = [
            {"record_id": "a", "category": "destructive_command", "valid": True, "expected": "no", "predicted": "yes"},
            {"record_id": "b", "category": "destructive_command", "valid": True, "expected": "no", "predicted": "no"},
            {"record_id": "c", "category": "destructive_command", "valid": True, "expected": "yes", "predicted": "no"},
            {"record_id": "d", "category": "destructive_command", "valid": False, "expected": "yes", "predicted": None},
        ]
        result = score_eval.destructive_confusion(rows)
        self.assertEqual(result["n"], 3)
        self.assertEqual(result["false_allow"], 1)
        self.assertEqual(result["false_deny"], 1)
        self.assertAlmostEqual(result["false_allow_rate"], 0.5)


if __name__ == "__main__":
    unittest.main()
