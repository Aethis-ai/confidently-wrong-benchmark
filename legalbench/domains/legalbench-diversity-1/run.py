#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["datasets>=2.14", "requests>=2.28"]
# ///
"""Phase 1 vertical slice — engine only, small N, no LLM baselines yet.

Pulls a slice from LegalBench `diversity_*` (HuggingFace `nguha/legalbench`),
deterministically extracts the three atomic fields from each case's templated
narrative, calls the local engine /decide endpoint, and reports correct/total.

We deliberately skip frontier-LLM baselines until the engine numbers are in —
we already know the LLMs work on this task; the open question is whether
Aethis encodes the rule.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

import requests
from datasets import load_dataset


def _load_bundle_id() -> str:
    """Read bundle_id from .aethis/state.json (CLI-canonical location)."""
    state_path = Path(__file__).parent / ".aethis" / "state.json"
    if not state_path.exists():
        raise SystemExit(
            f"missing {state_path} — author the bundle first "
            f"(via aethis-cli `aethis generate` or MCP `aethis_create_bundle`)"
        )
    return json.loads(state_path.read_text())["bundle_id"]


BUNDLE_ID = _load_bundle_id()


# Templated case format: "X is from STATE_A. Y is from STATE_B. X sues Y for CLAIM for $AMOUNT."
# E.g. "James is from Arizona. Lucas is from Arizona. James sues Lucas for negligence for $64,000."
_CASE_RE = re.compile(
    r"^(?P<p>[A-Z][a-z]+) is from (?P<ps>[A-Z][a-z]+(?: [A-Z][a-z]+)?)\. "
    r"(?P<d>[A-Z][a-z]+) is from (?P<ds>[A-Z][a-z]+(?: [A-Z][a-z]+)?)\. "
    r"(?P=p) sues (?P=d) for [^$]+\$(?P<amt>[\d,]+)\.?$",
)


def extract_fields(text: str) -> dict[str, Any] | None:
    """Deterministically pull (plaintiff_state, defendant_state, amount) from
    the templated narrative. Returns None if the regex doesn't match."""
    m = _CASE_RE.match(text.strip())
    if not m:
        return None
    return {
        "plaintiff_state": m.group("ps"),
        "defendant_state": m.group("ds"),
        "claim_amount_usd": int(m.group("amt").replace(",", "")),
    }


def decide(engine_url: str, api_key: str, field_values: dict) -> dict:
    resp = requests.post(
        f"{engine_url.rstrip('/')}/api/v1/public/decide",
        json={"bundle_id": BUNDLE_ID, "field_values": field_values},
        headers={"X-API-Key": api_key} if api_key else {},
        timeout=30,
    )
    if resp.status_code != 200:
        return {"error": f"HTTP {resp.status_code}: {resp.text[:200]}"}
    return resp.json()


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("--task", default="diversity_1", help="LegalBench subtask")
    p.add_argument("--limit", type=int, default=10, help="First N test cases")
    p.add_argument("--split", default="test", choices=["train", "test"])
    p.add_argument("--engine-url", default="http://127.0.0.1:8080")
    p.add_argument("--api-key", default="test")
    p.add_argument("--output", type=Path)
    args = p.parse_args()

    ds = load_dataset("nguha/legalbench", args.task)
    rows = ds[args.split].select(range(min(args.limit, len(ds[args.split]))))
    print(f"Slice: {args.task}/{args.split}, N={len(rows)}", file=sys.stderr)

    per_case: list[dict] = []
    correct = 0
    extract_fail = 0
    engine_err = 0

    for i, row in enumerate(rows):
        text = row["text"]
        expected_yes = row["answer"].strip().lower() == "yes"
        expected_decision = "eligible" if expected_yes else "not_eligible"

        fv = extract_fields(text)
        if fv is None:
            extract_fail += 1
            per_case.append({
                "index": row["index"],
                "text": text,
                "expected": expected_decision,
                "status": "extract_fail",
            })
            print(f"  [{i+1:>3}] EXTRACT_FAIL  {text[:70]!r}")
            continue

        resp = decide(args.engine_url, args.api_key, fv)
        if "error" in resp:
            engine_err += 1
            per_case.append({
                "index": row["index"],
                "text": text,
                "expected": expected_decision,
                "field_values": fv,
                "status": f"engine_err: {resp['error']}",
            })
            print(f"  [{i+1:>3}] ENGINE_ERR    {resp['error']}")
            continue

        decision = resp.get("decision")
        ok = decision == expected_decision
        if ok:
            correct += 1
        per_case.append({
            "index": row["index"],
            "text": text,
            "expected": expected_decision,
            "field_values": fv,
            "decision": decision,
            "correct": ok,
        })
        status = "OK " if ok else "BAD"
        print(f"  [{i+1:>3}] {status}  exp={expected_decision:<13} got={decision:<13} "
              f"{fv['plaintiff_state']!r}/{fv['defendant_state']!r} ${fv['claim_amount_usd']:,}")

    total = len(rows)
    print()
    print(f"Engine: {correct}/{total}  ({100*correct/total:.1f}%)")
    print(f"  extract_fail = {extract_fail}, engine_err = {engine_err}")

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps({
            "task": args.task,
            "split": args.split,
            "limit": args.limit,
            "bundle_id": BUNDLE_ID,
            "engine_url": args.engine_url,
            "summary": {
                "correct": correct,
                "total": total,
                "extract_fail": extract_fail,
                "engine_err": engine_err,
            },
            "per_case": per_case,
        }, indent=2))
        print(f"Wrote {args.output}")

    return 0 if (correct == total and extract_fail == 0) else 1


if __name__ == "__main__":
    sys.exit(main())
