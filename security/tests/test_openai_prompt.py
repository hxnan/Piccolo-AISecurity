#!/usr/bin/env python3
"""Offline tests for the OpenAI-compatible prompt template and parser."""
from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from openai_prompt import (  # noqa: E402
    extract_json,
    option_items,
    parse_answer,
    render_prompt,
)


def record(question):
    return {
        "id": "test",
        "category": "destructive_command",
        "source": {"benchmark": "self-extended"},
        "state": {"task": "clean", "shell": "bash", "cwd": "/tmp", "command": "rm -rf x"},
        "questions": {"decision": question},
    }


class PromptTest(unittest.TestCase):
    def test_noul_options(self):
        question = {"type": "noul", "instructions": "allow?", "criteria": {"false": "no", "true": "yes"}}
        self.assertEqual(option_items(question), [("yes", "yes"), ("no", "no")])

    def test_score_options(self):
        question = {"type": "score", "instructions": "level?", "criteria": ["low", "mid", "high"]}
        self.assertEqual(option_items(question), [("0", "low"), ("1", "mid"), ("2", "high")])

    def test_choice_options_use_order(self):
        question = {"type": "choice", "instructions": "pick", "criteria": {"A": "a", "B": "b"},
                    "option_order": ["B", "A"]}
        self.assertEqual(option_items(question), [("B", "b"), ("A", "a")])

    def test_small_set_asks_for_probabilities(self):
        question = {"type": "choice", "instructions": "pick", "criteria": {"A": "a", "B": "b"}}
        _, user = render_prompt(record(question), "decision")
        self.assertIn("probabilities", user)
        self.assertNotIn("only answer and confidence", user)

    def test_large_set_asks_for_confidence_only(self):
        keys = {f"K{i}": f"option {i}" for i in range(12)}
        question = {"type": "choice", "instructions": "pick", "criteria": keys,
                    "option_order": list(keys)}
        _, user = render_prompt(record(question), "decision")
        self.assertIn("confidence", user)
        self.assertNotIn("Include every option in probabilities", user)

    def test_extract_json_code_fence(self):
        self.assertEqual(extract_json('```json\n{"answer": "yes"}\n```'), {"answer": "yes"})

    def test_extract_json_single_element_array(self):
        self.assertEqual(extract_json('[{"answer": "yes"}]'), {"answer": "yes"})

    def test_extract_json_rejects_ambiguous_array(self):
        with self.assertRaises(ValueError):
            extract_json('[{"tool": "a"}, {"tool": "b"}]')

    def test_extract_json_picks_strongest_answer(self):
        payload = extract_json(
            '[{"answer":"A","probabilities":{"A":0.2,"B":0.8}},'
            ' {"answer":"B","probabilities":{"A":0.9,"B":0.1}}]'
        )
        self.assertEqual(payload["answer"], "B")

    def test_parse_answer_accepts_decision_key(self):
        question = {"type": "choice", "criteria": {"A": "a", "B": "b"}}
        answer = parse_answer(question, {"decision": "A", "probabilities": {"A": 0.9, "B": 0.1}})
        self.assertEqual(answer["probabilities"]["A"], 0.9)

    def test_parse_answer_falls_back_to_probabilities(self):
        question = {"type": "choice", "criteria": {"A": "a", "B": "b"}}
        answer = parse_answer(question, {"probabilities": {"A": 0.2, "B": 0.8}})
        self.assertEqual(answer["probabilities"]["B"], 0.8)

    def test_parse_noul_aliases(self):
        question = {"type": "noul", "criteria": {"false": "no", "true": "yes"}}
        self.assertEqual(parse_answer(question, {"answer": "true", "probabilities": {"yes": 0.8, "no": 0.2}}),
                         {"type": "noul", "noul": 0.8})

    def test_parse_score_type(self):
        question = {"type": "score", "criteria": ["a", "b", "c"]}
        answer = parse_answer(question, {"answer": 2, "probabilities": {"0": 0.1, "1": 0.2, "2": 0.7}})
        self.assertEqual(answer["type"], "score")
        self.assertEqual(answer["probabilities"]["2"], 0.7)

    def test_parse_large_set_confidence(self):
        keys = [f"K{i}" for i in range(12)]
        question = {"type": "choice", "criteria": {key: key for key in keys}, "option_order": keys}
        answer = parse_answer(question, {"answer": "K3", "confidence": 0.9})
        self.assertAlmostEqual(sum(answer["probabilities"].values()), 1.0)
        self.assertGreater(answer["probabilities"]["K3"], 0.8)

    def test_invalid_answer_rejected(self):
        question = {"type": "choice", "criteria": {"A": "a", "B": "b"}}
        with self.assertRaises(ValueError):
            parse_answer(question, {"answer": "C", "probabilities": {"A": 0.5, "B": 0.5}})


if __name__ == "__main__":
    unittest.main()
