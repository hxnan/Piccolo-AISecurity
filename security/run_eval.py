#!/usr/bin/env python3
"""Run the AISecurity set against a Piccolo ``/v1/systemone`` server.

One request is sent per question, matching the official Harness evaluation
granularity. Every response is archived before scoring so the GPU session can
be shut down early and scoring can be repeated offline.

Usage on the GPU host:
    python security/run_eval.py \
        --base-url http://127.0.0.1:18604 \
        --model piccolo-0.8b-vl \
        --api-key-env PICCOLO_API_KEY \
        --output-dir var/eval/0.8b-baseline \
        --workers 8
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import random
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
DEFAULT_DATASET = HERE / "ais_security_v5.jsonl"


def read_jsonl(path: Path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def write_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def option_keys(question: dict) -> list:
    if question["type"] == "noul":
        return ["yes", "no"]
    if question["type"] == "score":
        return [str(i) for i in range(len(question["criteria"]))]
    return [str(key) for key in (question.get("option_order") or question["criteria"])]


def wire_question(question: dict) -> dict:
    return {key: question[key] for key in ("type", "instructions", "criteria", "option_order") if key in question}


def validate_answer(answer, question: dict) -> str:
    if not isinstance(answer, dict):
        raise ValueError("answer is not an object")
    if answer.get("type") != question["type"]:
        raise ValueError(f"answer type {answer.get('type')!r} != {question['type']!r}")
    if question["type"] == "noul":
        value = answer.get("noul")
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError("noul must be a number")
        if not 0.0 <= float(value) <= 1.0:
            raise ValueError("noul outside [0, 1]")
        return ""
    probabilities = answer.get("probabilities")
    if not isinstance(probabilities, dict):
        raise ValueError("probabilities missing")
    expected = set(option_keys(question))
    if set(probabilities) != expected:
        raise ValueError(
            "probability keys differ: missing=%s extra=%s"
            % (sorted(expected - set(probabilities)), sorted(set(probabilities) - expected))
        )
    total = 0.0
    for key, value in probabilities.items():
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError(f"probability {key!r} is not numeric")
        if not 0.0 <= float(value) <= 1.0:
            raise ValueError(f"probability {key!r} outside [0, 1]")
        total += float(value)
    if abs(total - 1.0) > 2e-2:
        raise ValueError(f"probabilities sum to {total:.6f}")
    return f"{total:.6f}"


def get_json(url: str, key: str, timeout: float) -> dict:
    request = urllib.request.Request(url, headers={"Authorization": f"Bearer {key}"} if key else {})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def post_json(url: str, payload: dict, key: str, timeout: float):
    data = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    if key:
        headers["Authorization"] = "Bearer " + key
    request = urllib.request.Request(url, data=data, headers=headers)
    started = time.monotonic()
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.status, response.read().decode("utf-8", "replace"), time.monotonic() - started
    except urllib.error.HTTPError as error:
        return error.code, error.read().decode("utf-8", "replace"), time.monotonic() - started


def build_tasks(rows, limit=None, only_ids=None):
    tasks = []
    for row in rows:
        if only_ids and row["id"] not in only_ids:
            continue
        for qid, question in row["questions"].items():
            tasks.append(
                {
                    "record_id": row["id"],
                    "question_id": qid,
                    "state": row["state"],
                    "question": question,
                    "source": row["source"]["benchmark"],
                    "category": row["category"],
                    "language": row["source"].get("language"),
                    "difficulty": row["source"].get("difficulty"),
                }
            )
    if limit is not None:
        tasks = tasks[:limit]
    return tasks


def run_one(url, model, key, timeout, retries, task):
    base = {name: task[name] for name in
            ("record_id", "question_id", "source", "category", "language", "difficulty")}
    payload = {
        "model": model,
        "state": task["state"],
        "questions": {task["question_id"]: wire_question(task["question"])},
    }
    last = None
    for attempt in range(retries + 1):
        try:
            status, text, seconds = post_json(url, payload, key, timeout)
        except (OSError, urllib.error.URLError, TimeoutError) as error:
            last = {"status": None, "error": f"{type(error).__name__}: {error}", "seconds": 0.0}
            if attempt < retries:
                time.sleep(1.5 * (attempt + 1))
                continue
            return dict(base, ok=False, attempts=attempt + 1, **last)
        parsed = None
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            pass
        if status == 200 and isinstance(parsed, dict):
            try:
                answers = parsed.get("answers")
                if not isinstance(answers, dict) or set(answers) != {task["question_id"]}:
                    raise ValueError("answers keys differ from the request")
                prob_sum = validate_answer(answers[task["question_id"]], task["question"])
                if parsed.get("model") not in (None, model):
                    raise ValueError(f"served model {parsed.get('model')!r} != {model!r}")
                return dict(
                    base,
                    ok=True,
                    attempts=attempt + 1,
                    status=status,
                    seconds=seconds,
                    prob_sum=prob_sum,
                    answer=answers[task["question_id"]],
                    usage=parsed.get("usage"),
                    model=parsed.get("model"),
                    response=parsed,
                )
            except (KeyError, TypeError, ValueError) as error:
                last = {"status": status, "error": str(error), "seconds": seconds, "response": parsed}
        else:
            message = parsed.get("error") if isinstance(parsed, dict) else text[:500]
            last = {"status": status, "error": str(message)[:1000], "seconds": seconds, "response": parsed}
            if status in (401, 403, 404):
                return dict(base, ok=False, attempts=attempt + 1, critical=True, **last)
            if status == 422:
                return dict(base, ok=False, attempts=attempt + 1, context_exceeded=True, **last)
        if status not in (408, 429, 500, 502, 503, 504):
            break
        if attempt < retries:
            time.sleep(1.5 * (attempt + 1))
    return dict(base, ok=False, attempts=attempt + 1, **last)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--base-url", default="http://127.0.0.1:18604")
    parser.add_argument("--model", default="piccolo-0.8b-vl")
    parser.add_argument("--api-key-env", default="PICCOLO_API_KEY")
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--timeout", type=float, default=300.0)
    parser.add_argument("--retries", type=int, default=2)
    parser.add_argument("--limit", type=int, help="run only the first N questions")
    parser.add_argument("--ids", nargs="*", help="run only these record ids")
    parser.add_argument("--resume", action="store_true", help="skip successful (record, question) pairs")
    parser.add_argument("--progress-every", type=int, default=20)
    args = parser.parse_args(argv)

    if args.workers < 1 or args.timeout <= 0 or args.retries < 0:
        parser.error("workers/timeout/retries must be positive")
    key = os.environ.get(args.api_key_env, "") if args.api_key_env else ""
    rows = read_jsonl(args.dataset)
    tasks = build_tasks(rows, args.limit, set(args.ids) if args.ids else None)
    if not tasks:
        parser.error("no tasks selected")

    output = args.output_dir.resolve()
    output.mkdir(parents=True, exist_ok=True)
    raw_path = output / "raw.jsonl"
    done = set()
    if raw_path.exists():
        if not args.resume:
            parser.error(f"{raw_path} exists; pass --resume or choose a new --output-dir")
        for row in read_jsonl(raw_path):
            if row.get("ok"):
                done.add((row["record_id"], row["question_id"]))
    todo = [task for task in tasks if (task["record_id"], task["question_id"]) not in done]

    endpoint = args.base_url.rstrip("/") + "/v1/systemone"
    health_url = args.base_url.rstrip("/") + "/health"
    info_url = args.base_url.rstrip("/") + "/server_info"
    health = info = None
    try:
        health = get_json(health_url, key, 30)
        info = get_json(info_url, key, 30)
    except Exception as error:  # noqa: BLE001 - diagnostics only
        print(f"warning: server probe failed: {error}", file=sys.stderr)

    meta = {
        "dataset": str(args.dataset),
        "dataset_sha256": hashlib.sha256(args.dataset.read_bytes()).hexdigest(),
        "model": args.model,
        "endpoint": endpoint,
        "workers": args.workers,
        "timeout_seconds": args.timeout,
        "retries": args.retries,
        "questions_total": len(tasks),
        "questions_pending": len(todo),
        "started_utc": datetime.now(timezone.utc).isoformat(),
        "runner_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "health": health,
        "server_info": info,
    }
    try:
        meta["repo_commit"] = subprocess.check_output(
            ["git", "-C", str(ROOT), "rev-parse", "HEAD"], text=True, stderr=subprocess.DEVNULL
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        meta["repo_commit"] = None
    write_json(output / "run.json", meta)

    print(f"dataset {meta['dataset_sha256'][:12]} | {len(tasks)} questions | {len(todo)} pending")
    started = time.monotonic()
    lock = threading.Lock()
    completed = 0
    failures = 0
    orders = list(range(len(todo)))
    random.Random(42).shuffle(orders)

    def ordered(i):
        return todo[orders[i]]

    with raw_path.open("a", encoding="utf-8") as stream, ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {pool.submit(run_one, endpoint, args.model, key, args.timeout, args.retries, ordered(i)): i
                   for i in range(len(todo))}
        for future in as_completed(futures):
            result = future.result()
            with lock:
                stream.write(json.dumps(result, ensure_ascii=False) + "\n")
                stream.flush()
                completed += 1
                if not result.get("ok"):
                    failures += 1
                if completed % args.progress_every == 0 or completed == len(todo):
                    elapsed = time.monotonic() - started
                    rate = completed / elapsed if elapsed else 0
                    print(f"{completed}/{len(todo)} done | {failures} failed | {rate:.1f} q/s")
            if result.get("critical"):
                print(f"critical server error: {result.get('error')}", file=sys.stderr)
                for pending in futures:
                    pending.cancel()
                break

    meta.update(
        finished_utc=datetime.now(timezone.utc).isoformat(),
        seconds=round(time.monotonic() - started, 2),
        completed=completed + len(done) if args.resume else completed,
        failures=failures,
        skipped_existing=len(done),
    )
    write_json(output / "run.json", meta)
    print(f"raw responses: {raw_path}")
    print(f"failures: {failures}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
