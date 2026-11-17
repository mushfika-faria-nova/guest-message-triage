"""Eval runner: sends every case in cases.jsonl through the real triage() and grades the result.

Run from the repo root:
    uv run --env-file .env python evals/run.py --limit 3          # pilot
    uv run --env-file .env python evals/run.py                     # full run, baseline
    uv run --env-file .env python evals/run.py --variant v1 --model claude-sonnet-5-5

Output goes to evals/runs/<variant>/:
    results.jsonl  one graded row per (case, rep), written as each one finishes
    traces/        the full exchange for each (case, rep)
    errors.jsonl   attempts that never produced a gradable reply (API error, timeout)
A rerun skips (case, rep) pairs already in results.jsonl, so a crash loses nothing.
"""

import argparse
import hashlib
import json
import math
import re
import sys
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import anthropic

from guest_message_triage.triage import MODEL, SYSTEM_PROMPT, triage

EVALS = Path(__file__).parent
CASES = EVALS / "cases.jsonl"
RUNS = EVALS / "runs"
STATE = RUNS / "_state.json"

# Files whose change means earlier results are no longer comparable.
HARNESS_FILES = [
    Path(__file__),
    CASES,
    EVALS.parent / "src" / "guest_message_triage" / "triage.py",
]

# $ per million tokens (first-party prices). Used only for the summary line.
PRICES = {
    "claude-haiku-5-5": (0.10, 0.50),
    "claude-sonnet-5-5": (2.00, 10.00),
}

# Ticket fields are graded only when the expected answer is "no review":
# for review cases the person reads the message anyway (agreed grading method).
METRICS = [
    {"id": "needs_review", "label": "needs_review", "kind": "binary"},
    {"id": "ticket_count", "label": "ticket count", "kind": "binary"},
    {"id": "category", "label": "category", "kind": "binary"},
    {"id": "urgency", "label": "urgency", "kind": "float", "scale": 1},
    {"id": "unit", "label": "unit", "kind": "float", "scale": 1},
]


# ---------- grading ----------

def norm_unit(unit):
    """Labelling rule 3: "Room 201", "roo 201" and "201" all count as "201"."""
    if unit is None:
        return None
    unit = unit.strip().lower()
    return re.sub(r"^(unit|room|roo|apt\.?|apartment|flat)\s+", "", unit)


def share_matched(expected, got):
    """Share of expected items found in got, each got item used once (multiset match)."""
    if not expected:
        return 1.0
    left = Counter(got)
    hits = 0
    for item in expected:
        if left[item] > 0:
            left[item] -= 1
            hits += 1
    return hits / len(expected)


def grade(expected, output):
    scores = {"needs_review": int(output["needs_review"] == expected["needs_review"])}
    if expected["needs_review"]:
        return scores
    exp, got = expected["tickets"], output["tickets"]
    scores["ticket_count"] = int(len(got) == len(exp))
    scores["category"] = int(sorted(t["category"] for t in got) == sorted(t["category"] for t in exp))
    # Urgency is checked per ticket, matched by category, so two tickets in a
    # different order still count.
    scores["urgency"] = share_matched(
        [(t["category"], t["urgency"]) for t in exp], [(t["category"], t["urgency"]) for t in got]
    )
    # Unit is checked on its own, so a wrong category isn't counted a second time here.
    scores["unit"] = share_matched(
        [norm_unit(t["unit"]) for t in exp], [norm_unit(t["unit"]) for t in got]
    )
    return scores


# ---------- calling the app ----------

class RecordingMessages:
    """Wraps client.messages so the runner can read model, usage and stop_reason
    of the call triage() made, without changing triage() itself."""

    def __init__(self, messages):
        self._messages = messages
        self.last = None

    def parse(self, **kwargs):
        self.last = None
        self.last = self._messages.parse(**kwargs)
        return self.last


class RecordingClient:
    def __init__(self, client):
        self.messages = RecordingMessages(client.messages)


def run_case(client, case, rep, model):
    rec = RecordingClient(client)
    start = time.monotonic()
    result = triage(rec, case["text"], model=model)
    latency = time.monotonic() - start
    response = rec.messages.last
    output = result.model_dump()

    row = {
        "prompt_id": case["id"],
        "prompt": case["text"],
        "tags": case["tags"],
        "rep": rep,
        "status": "ok",
        "latency_s": round(latency, 2),
        "meta": {"expected": case["expected"], "output": output},
    }
    if response is None:
        # parse() raised ValidationError inside triage(), which then fell back to review.
        # No usage is available for this call.
        row["stop_reason"] = None
        row["meta"]["fallback"] = "invalid_reply"
    else:
        if not response.model.startswith(model):
            raise RuntimeError(f"served model {response.model} != requested {model}")
        row["model"] = response.model
        row["stop_reason"] = response.stop_reason
        row["usage"] = {
            "input_tokens": response.usage.input_tokens,
            "output_tokens": response.usage.output_tokens,
            "cache_read_input_tokens": response.usage.cache_read_input_tokens or 0,
            "cache_creation_input_tokens": response.usage.cache_creation_input_tokens or 0,
        }
        if response.stop_reason == "max_tokens":
            row["status"] = "truncated"  # counted, but left out of the means
    row["grade"] = grade(case["expected"], output) if row["status"] == "ok" else {}

    trace = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": case["text"]},
        {"role": "assistant", "content": json.dumps(output, indent=2)},
    ]
    return row, trace


# ---------- bookkeeping ----------

def harness_sha():
    h = hashlib.sha256()
    for f in HARNESS_FILES:
        h.update(f.read_bytes())
    return h.hexdigest()


def check_harness(approve):
    state = json.loads(STATE.read_text()) if STATE.exists() else {}
    sha = harness_sha()
    if approve:
        state.update({"metrics": METRICS, "harness_sha": sha})
        RUNS.mkdir(parents=True, exist_ok=True)
        STATE.write_text(json.dumps(state, indent=2))
        print("harness approved")
    elif state.get("harness_sha") != sha:
        sys.exit("runner, cases or triage.py changed since the last approval: "
                 "read the change, then rerun with --approve-harness")


def done_keys(results):
    if not results.exists():
        return set()
    return {(r["prompt_id"], r["rep"]) for r in map(json.loads, results.read_text().splitlines())}


def summarise(results):
    rows = [json.loads(line) for line in results.read_text().splitlines()]
    ok = [r for r in rows if r["status"] == "ok"]
    print(f"\n{len(rows)} rows ({len(ok)} ok, {len(rows) - len(ok)} truncated)")
    for m in METRICS:
        # Mean per case over its reps first, then over cases.
        per_case = {}
        for r in ok:
            if m["id"] in r["grade"]:
                per_case.setdefault(r["prompt_id"], []).append(r["grade"][m["id"]])
        means = [sum(v) / len(v) for v in per_case.values()]
        if not means:
            continue
        mean = sum(means) / len(means)
        half = 1.96 * math.sqrt(mean * (1 - mean) / len(means)) if len(means) > 1 else 0
        print(f"  {m['label']:<13} {mean:6.1%}  ±{half:5.1%}  over {len(means)} cases")
    cost, priced = 0.0, 0
    for r in rows:
        model = r.get("model", "")
        price = next((p for name, p in PRICES.items() if model.startswith(name)), None)
        if price and "usage" in r:
            u = r["usage"]
            cost += (u["input_tokens"] * price[0] + u["output_tokens"] * price[1]
                     + u["cache_read_input_tokens"] * price[0] * 0.1
                     + u["cache_creation_input_tokens"] * price[0] * 1.25) / 1e6
            priced += 1
    print(f"  cost ${cost:.4f} for {priced} calls ({len(rows) - priced} not measured)")


def regrade(variant):
    """Grade a finished run again against the current labels, using the saved outputs.
    No API calls: for when a label was fixed after the run."""
    expected = {c["id"]: c["expected"] for c in map(json.loads, CASES.read_text().splitlines())}
    results = RUNS / variant / "results.jsonl"
    rows = [json.loads(line) for line in results.read_text().splitlines()]
    for r in rows:
        r["meta"]["expected"] = expected[r["prompt_id"]]
        if r["status"] == "ok":
            r["grade"] = grade(r["meta"]["expected"], r["meta"]["output"])
    results.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows))
    print(f"regraded {len(rows)} rows in {variant}")
    summarise(results)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--variant", default="baseline", help="baseline, v1, v2, ...")
    ap.add_argument("--model", default=MODEL)
    ap.add_argument("--reps", type=int, default=2)
    ap.add_argument("--limit", type=int, help="only the first N cases (pilot)")
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--timeout-s", type=float, default=150, help="wall-clock ceiling per case")
    ap.add_argument("--approve-harness", action="store_true")
    ap.add_argument("--regrade", action="store_true", help="re-grade saved outputs, no API calls")
    args = ap.parse_args()
    if not re.fullmatch(r"baseline|v\d+", args.variant):
        sys.exit("variant must be baseline or v<N> (the report ignores other names)")
    if args.regrade:
        regrade(args.variant)
        return

    check_harness(args.approve_harness)
    cases = [json.loads(line) for line in CASES.read_text().splitlines()][: args.limit]
    out = RUNS / args.variant
    (out / "traces").mkdir(parents=True, exist_ok=True)
    results, errors = out / "results.jsonl", out / "errors.jsonl"
    done = done_keys(results)
    todo = [(c, rep) for c in cases for rep in range(args.reps) if (c["id"], rep) not in done]
    print(f"{len(todo)} calls to make on {args.model} ({len(done)} already done)")

    # Same client settings as the app: 30 s timeout, SDK retries 429/5xx twice with backoff.
    client = anthropic.Anthropic(timeout=30.0, max_retries=2)
    with ThreadPoolExecutor(args.workers) as pool:
        futures = {pool.submit(run_case, client, c, rep, args.model): (c, rep) for c, rep in todo}
        for future, (case, rep) in futures.items():
            try:
                row, trace = future.result(timeout=args.timeout_s)
            except Exception as e:  # API error after retries, timeout, wrong model
                with errors.open("a") as f:
                    f.write(json.dumps({"prompt_id": case["id"], "rep": rep,
                                        "class": type(e).__name__, "error": str(e)[:300]}) + "\n")
                print(f"  {case['id']} rep {rep}: {type(e).__name__}")
                continue
            (out / "traces" / f"{case['id']}_rep{rep}.json").write_text(json.dumps(trace, indent=2))
            with results.open("a") as f:
                f.write(json.dumps(row, ensure_ascii=False) + "\n")
            print(f"  {case['id']} rep {rep}: {row['grade']}")

    summarise(results)


if __name__ == "__main__":
    main()
