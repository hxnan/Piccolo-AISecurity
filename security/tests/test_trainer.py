#!/usr/bin/env python3
"""Offline checks for the LoRA trainer's candidate-target mapping."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

TESTS = Path(__file__).resolve().parent
SECURITY = TESTS.parent
sys.path.insert(0, str(SECURITY))

import train_lora_peft  # noqa: E402


class TrainerTargetTest(unittest.TestCase):
    def test_noul_bool_keys(self):
        row = SimpleNamespace(option_keys=(False, True))
        self.assertEqual(train_lora_peft.candidate_target(row, "noul", False), 0)
        self.assertEqual(train_lora_peft.candidate_target(row, "noul", True), 1)

    def test_noul_text_keys(self):
        row = SimpleNamespace(option_keys=("no", "yes"))
        self.assertEqual(train_lora_peft.candidate_target(row, "noul", "no"), 0)
        self.assertEqual(train_lora_peft.candidate_target(row, "noul", "yes"), 1)

    def test_choice(self):
        row = SimpleNamespace(option_keys=("approve", "refuse", "review"))
        self.assertEqual(train_lora_peft.candidate_target(row, "choice", "review"), 2)
        with self.assertRaises(ValueError):
            train_lora_peft.candidate_target(row, "choice", "missing")

    def test_score(self):
        row = SimpleNamespace(option_keys=("0", "1", "2"))
        self.assertEqual(train_lora_peft.candidate_target(row, "score", 1), 1)


if __name__ == "__main__":
    unittest.main()
