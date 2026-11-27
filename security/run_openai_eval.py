#!/usr/bin/env python3
"""Evaluate an OpenAI-compatible chat model on the Piccolo AISecurity set.

The native Piccolo server exposes candidate-token probabilities.  This runner
asks a chat model for a strict JSON answer plus a probability for each option,
then writes the same raw/scores schema used by ``score_eval.py``.

The API key is read from an environment variable and is never written to disk.
"""
from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import json
import os
import random
import threading
import time
from pathlib import Path

import requests

from openai_prompt import extract_json, parse_answer, render_prompt


def read_jsonl(path: Path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def write_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def post_chat(session: requests.Session, url: str, key: str, model: str, system: str, user: str,
              max_tokens: int, timeout: float, use_response_format: bool) -> requests.Response:
    payload = {
        "model": model,
        "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
        "temperature": 0,
        "top_p": 1,
        "max_tokens": max_tokens,
        "stream": False,
        "enable_thinking": False,
    }
    if use_response_format:
        payload["response_format"] = {"type": "json_object"}
    return session.post(url, headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
                        json=payload, timeout=timeout)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", default="security/ais_security_v5.jsonl")
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--model", default="qwen3.8-27b")
    parser.add_argument("--api-key-env", default="QWEN_API_KEY")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--timeout", type=float, default=300.0)
    parser.add_argument("--retries", type=int, default=2)
    parser.add_argument("--max-tokens", type=int, default=2048)
    parser.add_argument("--limit", type=int, default=0, help="only the first N questions")
    parser.add_argument("--progress-every", type=int, default=25)
    parser.add_argument("--no-response-format", action="store_true")
    args = parser.parse_args()

    key = os.environ.get(args.api_key_env)
    if not key:
        raise SystemExit(f"missing API key in environment variable {args.api_key_env}")
    base_url = args.base_url.rstrip("/")
    url = f"{base_url}/chat/completions"
    dataset = Path(args.dataset)
    rows = read_jsonl(dataset)
    questions = []
    for record in rows:
        for question_id in record["questions"]:
            questions.append((record, question_id))
    if args.limit:
        questions = questions[: args.limit]

    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)
    started = time.time()
    lock = threading.Lock()
    state = {"use_response_format": not args.no_response_format, "completed": 0, "failed": 0}

    def evaluate_one(item):
        record, question_id = item
        system, user = render_prompt(record, question_id)
        prompt_sha = hashlib.sha256((system + "\n" + user).encode("utf-8")).hexdigest()
        last = None
        for attempt in range(1, args.retries + 2):
            t0 = time.monotonic()
            user_for_attempt = user
            if attempt > 1:
                user_for_attempt = user + (
                    "\n\nIMPORTANT: Your previous output was invalid. Return exactly one JSON object "
                    "with the requested keys. Do not return a list, a tool call, or multiple objects."
                )
            try:
                session = requests.Session()
                with lock:
                    use_format = state["use_response_format"]
                response = post_chat(session, url, key, args.model, system, user_for_attempt,
                                     args.max_tokens, args.timeout, use_format)
                seconds = time.monotonic() - t0
                if response.status_code == 400 and use_format and "response_format" in response.text.lower():
                    with lock:
                        state["use_response_format"] = False
                    response = post_chat(session, url, key, args.model, system, user_for_attempt,
                                         args.max_tokens, args.timeout, False)
                    seconds = time.monotonic() - t0
                if response.status_code in (429, 500, 502, 503, 504) and attempt <= args.retries:
                    time.sleep(min(20, (2 ** attempt) + random.random()))
                    continue
                if response.status_code != 200:
                    last = {"ok": False, "status": response.status_code, "attempts": attempt,
                            "seconds": round(seconds, 4), "error": response.text[:1000],
                            "prompt_sha256": prompt_sha, "prompt_chars": len(system) + len(user)}
                    if response.status_code >= 500 and attempt <= args.retries:
                        continue
                    return last
                data = response.json()
                choice = (data.get("choices") or [{}])[0]
                message = choice.get("message") or {}
                content = message.get("content") or message.get("reasoning_content") or ""
                parsed = extract_json(content)
                answer = parse_answer(record["questions"][question_id], parsed)
                answer["prob_sum"] = round(sum(answer["probabilities"].values()), 6) if "probabilities" in answer else answer.get("noul")
                usage = data.get("usage") or {}
                return {
                    "record_id": record["id"],
                    "question_id": question_id,
                    "source": record["source"].get("benchmark"),
                    "category": record.get("category"),
                    "language": record.get("language"),
                    "difficulty": record.get("difficulty"),
                    "ok": True,
                    "attempts": attempt,
                    "status": response.status_code,
                    "seconds": round(seconds, 4),
                    "prob_sum": answer.pop("prob_sum", None),
                    "answer": answer,
                    "usage": usage,
                    "model": args.model,
                    "response": {
                        "id": data.get("id"),
                        "model": data.get("model"),
                        "finish_reason": choice.get("finish_reason"),
                        "content": content,
                        "reasoning_content": message.get("reasoning_content"),
                        "usage": usage,
                    },
                    "prompt_sha256": prompt_sha,
                    "prompt_chars": len(system) + len(user),
                }
            except Exception as error:  # noqa: BLE001 - network/parse diagnostics
                seconds = time.monotonic() - t0
                last = {"ok": False, "status": None, "attempts": attempt,
                        "seconds": round(seconds, 4), "error": f"{type(error).__name__}: {error}",
                        "prompt_sha256": prompt_sha, "prompt_chars": len(system) + len(user)}
                if attempt <= args.retries:
                    time.sleep(min(20, (2 ** attempt) + random.random()))
        return last

    raw_path = out / "raw.jsonl"
    failures = 0
    with raw_path.open("w", encoding="utf-8") as raw_file:
        with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
            futures = {pool.submit(evaluate_one, item): item for item in questions}
            for future in concurrent.futures.as_completed(futures):
                record, question_id = futures[future]
                result = future.result()
                if not result.get("ok"):
                    failures += 1
                    result.setdefault("record_id", record["id"])
                    result.setdefault("question_id", question_id)
                    result.setdefault("source", record["source"].get("benchmark"))
                    result.setdefault("category", record.get("category"))
                raw_file.write(json.dumps(result, ensure_ascii=False) + "\n")
                raw_file.flush()
                with lock:
                    state["completed"] += 1
                    completed = state["completed"]
                if completed % args.progress_every == 0 or completed == len(questions):
                    print(f"{completed}/{len(questions)} done | {failures} failed | "
                          f"{completed / max(0.001, time.time() - started):.1f} q/s")

    run = {
        "dataset": str(dataset),
        "dataset_sha256": hashlib.sha256(dataset.read_bytes()).hexdigest(),
        "model": args.model,
        "endpoint": url,
        "workers": args.workers,
        "timeout_seconds": args.timeout,
        "retries": args.retries,
        "questions_total": len(questions),
        "questions_pending": len(questions),
        "started_utc": time.strftime("%Y-%m-%dT%H:%M:%S+00:00", time.gmtime(started)),
        "finished_utc": time.strftime("%Y-%m-%dT%H:%M:%S+00:00", time.gmtime()),
        "seconds": round(time.time() - started, 2),
        "completed": len(questions),
        "failures": failures,
        "response_format": state["use_response_format"],
    }
    write_json(out / "run.json", run)
    print(f"raw responses: {raw_path}")
    print(f"failures: {failures}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
